import json
import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

import pytest
from claude_output import fake_claude_script
from rules_package import write_package

PROJECT = Path(__file__).resolve().parent.parent
SCRIPTS = sysconfig.get_path("scripts")
UNDER_TEST = {"CODEGUARD": str(Path(SCRIPTS) / "codeguard")}
UV = Path(shutil.which("uv") or "uv")
CLAUDE_CODE_COMMAND = 'uv run --quiet --script "${CLAUDE_PLUGIN_ROOT}/hooks/stop.py" claude-code'
CODEX_COMMAND = 'uv run --quiet --script "${CLAUDE_PLUGIN_ROOT}/hooks/stop.py" codex'
RULE_FILES_COMMAND = 'uv run --quiet --script "${CLAUDE_PLUGIN_ROOT}/hooks/rule_files.py"'
LOAD_THE_SKILL = (
    "Load codeguard's writing-rules skill before editing codeguard rule files: it holds "
    "the conventions for rules, gates, bindings and their cases. Invoke it with the Skill "
    "tool (codeguard:writing-rules), then make this edit again."
)
REQUIRED_FIXES = (
    "These errors are required fixes, not suggestions. Fix the code. If the fix needs a "
    "decision, ask the user. Don't change .codeguard/config.yaml to silence them."
)
NOT_REVIEWED = "codeguard review failed, so these changes were not reviewed."


def commands(config: Path, event: str) -> list[str]:
    hooks = json.loads(config.read_text())["hooks"]
    return [hook["command"] for group in hooks[event] for hook in group["hooks"]]


@pytest.fixture(autouse=True)
def home(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path_factory.mktemp("home")
    monkeypatch.setenv("HOME", str(path))
    return path


@pytest.fixture
def uv_only(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A PATH directory with uv and nothing else, so codeguard is not on PATH."""
    path = tmp_path_factory.mktemp("uv-only")
    (path / "uv").symlink_to(UV)
    return path


@pytest.fixture(scope="session")
def uv_cache() -> str:
    """uv's cache, found before a test moves HOME, so the plugin's environment syncs from it."""
    return subprocess.run(
        [UV, "cache", "dir"], capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def bundled(uv_cache: str) -> dict[str, str]:
    """What the plugin's own codeguard needs to sync its environment in a test."""
    return {"UV_CACHE_DIR": uv_cache, "UV_PYTHON": sys.executable}


@pytest.fixture
def claude_bin(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("claude-bin")


def put_claude(bin_dir: Path, script: str) -> None:
    claude = bin_dir / "claude"
    claude.write_text(script)
    claude.chmod(0o755)


def bind_skill(repo, make_skill) -> None:
    repo.write(".claude/skills/placement/SKILL.md", make_skill().text)
    repo.write(
        ".codeguard/bindings/placement.yaml",
        'skill: .claude/skills/placement\npaths: ["**/*.py"]\ntriggers: [any]\n',
    )
    repo.commit("Bind the skill")


def run_stop_hook(
    repo,
    hook_input: dict,
    command: str = CLAUDE_CODE_COMMAND,
    path: list[Path | str] | None = None,
    env: dict[str, str] | None = None,
) -> dict:
    """Run a hook config's command and return the one JSON object it must print.

    The hook runs the codeguard under test unless `env` replaces that override.
    """
    directories = path_with() if path is None else path
    result = subprocess.run(
        ["sh", "-c", command],
        cwd=repo.root,
        input=json.dumps(hook_input),
        capture_output=True,
        text=True,
        env={
            **without_codeguard(),
            **(UNDER_TEST if env is None else env),
            "CLAUDE_PLUGIN_ROOT": str(PROJECT),
            "CLAUDE_PROJECT_DIR": str(PROJECT),
            "PATH": os.pathsep.join(str(directory) for directory in directories),
        },
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def without_codeguard() -> dict[str, str]:
    return {name: value for name, value in os.environ.items() if name != "CODEGUARD"}


def path_with(*first: Path) -> list[Path | str]:
    return [*first, SCRIPTS, UV.parent, "/usr/bin", "/bin"]


def stop(stop_hook_active: bool = False) -> dict:
    return {"session_id": "session-1", "stop_hook_active": stop_hook_active}


class TestHookConfig:
    def test_claude_code_reviews_when_an_agent_stops(self):
        assert commands(PROJECT / "hooks" / "hooks.json", "Stop") == [CLAUDE_CODE_COMMAND]

    def test_claude_code_reviews_when_a_subagent_stops(self):
        assert commands(PROJECT / "hooks" / "hooks.json", "SubagentStop") == [CLAUDE_CODE_COMMAND]

    @pytest.mark.parametrize("event", ["Stop", "SubagentStop"])
    def test_codeguard_reviews_its_own_changes_with_its_development_version(
        self, repo, uv_only, make_diagnostic, event
    ):
        repo.write("a.py", "print(1)\n")
        [command] = commands(PROJECT / ".claude" / "settings.json", event)

        response = run_stop_hook(repo, stop(), command, path=[uv_only, "/usr/bin", "/bin"])

        assert response == {
            "decision": "block",
            "reason": f"{make_diagnostic()}\n{REQUIRED_FIXES}",
        }

    def test_a_session_installs_the_development_version_before_any_review(self, tmp_path):
        project = tmp_path / "project"
        project.mkdir()
        (project / "pyproject.toml").write_text(
            "[project]\n"
            'name = "tool"\n'
            'version = "0"\n'
            "[project.scripts]\n"
            'tool = "tool:main"\n'
            "[build-system]\n"
            'requires = ["uv_build>=0.10.11,<0.13"]\n'
            'build-backend = "uv_build"\n'
        )
        (project / "src" / "tool").mkdir(parents=True)
        (project / "src" / "tool" / "__init__.py").write_text("def main() -> None: ...\n")
        offline = {**os.environ, "UV_OFFLINE": "1"}
        subprocess.run([UV, "lock", "--quiet"], cwd=project, env=offline, check=True)
        [command] = commands(PROJECT / ".claude" / "settings.json", "SessionStart")

        result = subprocess.run(
            ["sh", "-c", command],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            env={**offline, "CLAUDE_PROJECT_DIR": str(project)},
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == ""
        assert (project / ".venv" / "bin" / "tool").exists()

    def test_claude_code_checks_edits_and_writes_to_rule_files(self):
        hooks = json.loads((PROJECT / "hooks" / "hooks.json").read_text())["hooks"]

        assert [
            (group["matcher"], [hook["command"] for hook in group["hooks"]])
            for group in hooks["PreToolUse"]
        ] == [("Edit|Write", [RULE_FILES_COMMAND])]

    def test_codex_reviews_when_an_agent_stops(self):
        assert commands(PROJECT / "hooks" / "codex.json", "Stop") == [CODEX_COMMAND]


class TestStopHook:
    def test_blocking_diagnostic_blocks_the_stop(self, repo, make_diagnostic):
        repo.write("a.py", "print(1)\n")

        response = run_stop_hook(repo, stop())

        assert response == {
            "decision": "block",
            "reason": f"{make_diagnostic()}\n{REQUIRED_FIXES}",
        }

    def test_ci_only_rule_does_not_run(self, repo):
        write_package(repo, prefix="rules/")
        repo.write(
            ".codeguard/config.yaml",
            "packages:\n"
            "  - kind: path\n"
            "    path: rules\n"
            "    rulesets:\n"
            "      python:\n"
            "        ci_only: true\n",
        )
        (repo.root / ".codeguard/rules/pattern/no-print.yml").unlink()
        repo.write("a.py", "print(1)\n")

        response = run_stop_hook(repo, stop())

        assert response == {}

    def test_the_same_error_blocks_every_time(self, repo):
        repo.write("a.py", "print(1)\n")
        run_stop_hook(repo, stop())

        response = run_stop_hook(repo, stop(stop_hook_active=True))

        assert response["decision"] == "block"

    def test_configured_warning_goes_to_the_user(self, repo, make_diagnostic):
        repo.write("a.py", "breakpoint()\n")

        response = run_stop_hook(repo, stop())

        assert response == {
            "systemMessage": f"codeguard warnings:\n{make_diagnostic(warning=True)}"
        }

    def test_only_blocking_items_reach_the_agent(self, repo, make_diagnostic):
        repo.write("a.py", "print(1)\nbreakpoint()\n")

        response = run_stop_hook(repo, stop())

        assert response == {
            "decision": "block",
            "reason": f"{make_diagnostic()}\n{REQUIRED_FIXES}",
            "systemMessage": f"codeguard warnings:\n{make_diagnostic(warning=True, line=2)}",
        }

    def test_low_confidence_finding_goes_to_the_user(
        self, repo, claude_bin, make_skill, make_diagnostic
    ):
        bind_skill(repo, make_skill)
        repo.write("a.py", "x = 1\n")
        violation = {"file": "a.py", "line": 1, "message": "Move it."}
        put_claude(claude_bin, fake_claude_script([{**violation, "confidence": 0.5}]))
        finding = make_diagnostic(
            judged=True,
            rule="placement",
            message="Move it.",
            note=None,
            warning=False,
            confidence=0.5,
        ).as_warning()

        response = run_stop_hook(repo, stop(), path=path_with(claude_bin))

        assert response == {"systemMessage": f"codeguard warnings:\n{finding}"}

    def test_judge_error_on_an_error_rule_goes_to_the_user(self, repo, claude_bin, make_skill):
        bind_skill(repo, make_skill)
        repo.write("a.py", "x = 1\n")
        put_claude(claude_bin, "#!/bin/sh\ncat > /dev/null\necho 'rate limited'\nexit 1\n")

        response = run_stop_hook(repo, stop(), path=path_with(claude_bin))

        assert list(response) == ["systemMessage"]
        assert response["systemMessage"].startswith(
            "codeguard warnings:\na.py: warning placement: The judge call failed"
        )

    def test_no_diagnostics_lets_the_agent_stop(self, repo):
        repo.write("a.py", "x = 1\n")

        assert run_stop_hook(repo, stop()) == {}

    def test_reports_without_editing_the_reviewed_file(self, repo):
        repo.write("a.py", "print(1)\n")

        run_stop_hook(repo, stop())

        assert (repo.root / "a.py").read_text() == "print(1)\n"

    def test_crashed_review_goes_to_the_user(self, repo):
        repo.write(".codeguard/rules/pattern/broken.yml", "id: [\n")
        repo.write("a.py", "print(1)\n")

        response = run_stop_hook(repo, stop())

        assert list(response) == ["systemMessage"]
        assert response["systemMessage"].startswith(
            f"{NOT_REVIEWED}\nError: Cannot parse rule {repo.root}/.codeguard/rules/pattern/"
            "broken.yml\n"
        )

    def test_the_plugin_reviews_with_the_codeguard_it_ships(
        self, repo, uv_only, bundled, tmp_path, make_diagnostic
    ):
        repo.write("a.py", "print(1)\n")
        data = tmp_path / "plugin-data"

        response = run_stop_hook(
            repo,
            stop(),
            path=[uv_only, "/usr/bin", "/bin"],
            env={**bundled, "CLAUDE_PLUGIN_DATA": str(data)},
        )

        assert response == {
            "decision": "block",
            "reason": f"{make_diagnostic()}\n{REQUIRED_FIXES}",
        }
        assert (data / "venv" / "bin" / "codeguard").exists()

    def test_missing_codeguard_goes_to_the_user(self, repo, tmp_path):
        missing = tmp_path / "codeguard"

        response = run_stop_hook(repo, stop(), env={"CODEGUARD": str(missing)})

        assert response == {
            "systemMessage": f"{NOT_REVIEWED}\n[Errno 2] No such file or directory: '{missing}'"
        }

    def test_claude_code_and_codex_get_the_same_response(self, repo):
        repo.write("a.py", "print(1)\nbreakpoint()\n")

        claude_code = run_stop_hook(repo, stop(), CLAUDE_CODE_COMMAND)
        codex = run_stop_hook(repo, {"session_id": "s", "turn_id": "t"}, CODEX_COMMAND)

        assert claude_code == codex


def transcript(tmp_path: Path, *tool_uses: dict) -> Path:
    """A session transcript in which the assistant made these tool calls."""
    path = tmp_path / "transcript.jsonl"
    entries = [{"type": "user", "message": {"role": "user", "content": "Write a rule."}}]
    entries += [
        {
            "type": "assistant",
            "message": {"role": "assistant", "content": [{"type": "tool_use", "id": "t", **use}]},
        }
        for use in tool_uses
    ]
    path.write_text("".join(f"{json.dumps(entry)}\n" for entry in entries))
    return path


def edit(root: Path, file: str, transcript_path: Path, tool: str = "Edit") -> dict:
    return {
        "session_id": "session-1",
        "transcript_path": str(transcript_path),
        "cwd": str(root),
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": {"file_path": file, "old_string": "a", "new_string": "b"},
    }


def run_rule_files_hook(root: Path, hook_input: dict) -> dict | None:
    result = subprocess.run(
        ["sh", "-c", RULE_FILES_COMMAND],
        cwd=root,
        input=json.dumps(hook_input),
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(PROJECT)},
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout) if result.stdout else None


DENIED = {
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": LOAD_THE_SKILL,
    }
}
SKILL_CALL = {"name": "Skill", "input": {"skill": "codeguard:writing-rules"}}


class TestRuleFilesHook:
    @pytest.mark.parametrize(
        "file",
        [
            ".codeguard/skills/placement/SKILL.md",
            ".codeguard/rules/pattern/no-print.yml",
            ".codeguard/gates/enum-value.yml",
            ".codeguard/bindings/placement.yaml",
            ".codeguard/rule-tests/no-print-test.yml",
            ".codeguard/rule-evals/placement.yaml",
        ],
    )
    def test_editing_a_rule_file_before_loading_the_skill_is_denied(self, tmp_path, file):
        response = run_rule_files_hook(tmp_path, edit(tmp_path, file, transcript(tmp_path)))

        assert response == DENIED

    def test_writing_a_rule_file_by_its_absolute_path_is_denied(self, tmp_path):
        file = str(tmp_path / ".codeguard/rules/pattern/no-print.yml")

        response = run_rule_files_hook(
            tmp_path, edit(tmp_path, file, transcript(tmp_path), tool="Write")
        )

        assert response == DENIED

    @pytest.mark.parametrize(
        "tool_use",
        [
            SKILL_CALL,
            {"name": "Skill", "input": {"skill": "writing-rules"}},
            {"name": "Read", "input": {"file_path": "/plugin/skills/writing-rules/SKILL.md"}},
        ],
        ids=["plugin-skill", "project-skill", "read-skill-file"],
    )
    def test_editing_a_rule_file_after_loading_the_skill_is_allowed(self, tmp_path, tool_use):
        hook_input = edit(tmp_path, ".codeguard/bindings/a.yaml", transcript(tmp_path, tool_use))

        assert run_rule_files_hook(tmp_path, hook_input) is None

    @pytest.mark.parametrize(
        "tool_use",
        [
            {"name": "Skill", "input": {"skill": "codeguard:writing-docs"}},
            {
                "name": "Read",
                "input": {"file_path": "/plugin/skills/writing-rules/references/python.md"},
            },
        ],
        ids=["another-skill", "a-reference-only"],
    )
    def test_other_tool_calls_do_not_count_as_loading_the_skill(self, tmp_path, tool_use):
        hook_input = edit(tmp_path, ".codeguard/bindings/a.yaml", transcript(tmp_path, tool_use))

        assert run_rule_files_hook(tmp_path, hook_input) == DENIED

    @pytest.mark.parametrize(
        "file", [".codeguard/config.yaml", "src/app.py", "docs/rules/pattern/x.yml"]
    )
    def test_other_files_are_not_checked(self, tmp_path, file):
        assert run_rule_files_hook(tmp_path, edit(tmp_path, file, transcript(tmp_path))) is None

    @pytest.mark.parametrize(
        "manifest",
        [
            "name: example\nrulesets: [python, ruby]\n",
            "name: example\nrulesets:\n  - python\n  - ruby\n",
        ],
        ids=["flow-list", "block-list"],
    )
    def test_editing_a_rule_file_in_a_package_ruleset_is_denied(self, tmp_path, manifest):
        (tmp_path / "codeguard-package.yaml").write_text(manifest)
        hook_input = edit(tmp_path, "ruby/rule-evals/placement.yaml", transcript(tmp_path))

        assert run_rule_files_hook(tmp_path, hook_input) == DENIED

    def test_a_directory_the_package_does_not_name_is_not_checked(self, tmp_path):
        (tmp_path / "codeguard-package.yaml").write_text("name: example\nrulesets: [python]\n")
        hook_input = edit(tmp_path, "scripts/rule-evals/notes.yaml", transcript(tmp_path))

        assert run_rule_files_hook(tmp_path, hook_input) is None

    def test_an_unreadable_transcript_lets_the_edit_through(self, tmp_path):
        hook_input = edit(tmp_path, ".codeguard/bindings/a.yaml", tmp_path / "missing.jsonl")

        assert run_rule_files_hook(tmp_path, hook_input) is None


class TestBundledCommand:
    def test_the_bash_tool_runs_the_codeguard_the_plugin_ships(self, uv_only, bundled, home):
        result = subprocess.run(
            [PROJECT / "bin" / "codeguard", "--help"],
            capture_output=True,
            text=True,
            env={
                **without_codeguard(),
                **bundled,
                "PATH": os.pathsep.join([str(uv_only), "/usr/bin", "/bin"]),
            },
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout.startswith("usage: codeguard")
        assert (home / ".cache" / "codeguard" / "venv" / "bin" / "codeguard").exists()
