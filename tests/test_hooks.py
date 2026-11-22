import json
import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

import pytest
from claude_output import claude_stream
from fake_cli import FAKE_CLAUDE, configure_fake_cli_response
from rules_package import write_package

pytestmark = pytest.mark.usefixtures("fake_cli_config")

PROJECT = Path(__file__).resolve().parent.parent
SCRIPTS = sysconfig.get_path("scripts")
PLACEMENT_BINDING = 'rule: placement\npaths: ["**/*.py"]\ntriggers: [any]\n'
UNDER_TEST = {"CODEGUARD": str(Path(SCRIPTS) / "codeguard")}
UV = Path(shutil.which("uv") or "uv")
CLAUDE_CODE_COMMAND = 'uv run --quiet --script "${CLAUDE_PLUGIN_ROOT}/hooks/stop.py" claude-code'
CODEX_COMMAND = 'uv run --quiet --script "${CLAUDE_PLUGIN_ROOT}/hooks/stop.py" codex'
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
def claude_bin() -> Path:
    return FAKE_CLAUDE.parent


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

        warning = make_diagnostic(warning=True, lines__start=2, lines__end=2)
        assert response == {
            "decision": "block",
            "reason": f"{make_diagnostic()}\n{REQUIRED_FIXES}",
            "systemMessage": f"codeguard warnings:\n{warning}",
        }

    def test_judged_error_finding_blocks_the_agent(
        self, repo, make_judge_rule, claude_bin, make_diagnostic
    ):
        repo.write(".codeguard/rules/judge/placement.md", make_judge_rule().text)
        repo.write(".codeguard/bindings/placement.yaml", PLACEMENT_BINDING)
        repo.commit("Bind the rule")
        repo.write("a.py", "x = 1\ny = 2\n")
        violation = {"file": "a.py", "lines": {"start": 1, "end": 2}, "message": "Move it."}
        configure_fake_cli_response({"stdout": claude_stream([violation])})
        finding = make_diagnostic(
            judged=True,
            lines__start=1,
            lines__end=2,
            rule="placement",
            message="Move it.",
            note=None,
            warning=False,
        )

        response = run_stop_hook(repo, stop(), path=path_with(claude_bin))

        assert response == {"decision": "block", "reason": f"{finding}\n{REQUIRED_FIXES}"}

    def test_judge_error_on_an_error_rule_goes_to_the_user(self, repo, make_judge_rule, claude_bin):
        repo.write(".codeguard/rules/judge/placement.md", make_judge_rule().text)
        repo.write(".codeguard/bindings/placement.yaml", PLACEMENT_BINDING)
        repo.commit("Bind the rule")
        repo.write("a.py", "x = 1\n")
        configure_fake_cli_response({"stdout": "rate limited\n", "exit_code": 1})

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
