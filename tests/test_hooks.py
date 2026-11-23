import json
import os
import shutil
import subprocess
import sysconfig
from pathlib import Path

import pytest
import yaml
from fake_cli import FAKE_CLAUDE, configure_fake_cli_response
from rules_package import write_package

PLUGIN = Path(__file__).resolve().parent.parent / "plugin"
SCRIPTS = sysconfig.get_path("scripts")
UNDER_TEST = {"CODEGUARD": str(Path(SCRIPTS) / "codeguard")}
UV = Path(shutil.which("uv") or "uv")
CLAUDE_CODE_COMMAND = 'uv run --quiet --script "${CLAUDE_PLUGIN_ROOT}/hooks/stop.py" claude-code'
CODEX_COMMAND = 'uv run --quiet --script "${CLAUDE_PLUGIN_ROOT}/hooks/stop.py" codex'
REQUIRED_FIXES = (
    "These errors are required fixes, not suggestions. Fix the code. If the fix needs a "
    "decision, ask the user. Don't change .codeguard/config.yaml to silence them."
)


def commands(config: Path, event: str) -> list[str]:
    hooks = json.loads(config.read_text())["hooks"]
    return [hook["command"] for group in hooks[event] for hook in group["hooks"]]


@pytest.fixture
def temporary_home(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path_factory.mktemp("home")))


def run_stop_hook(
    repo,
    hook_input: dict,
    command: str = CLAUDE_CODE_COMMAND,
    path: list[Path | str] | None = None,
) -> dict:
    """Run a hook config's command and return the one JSON object it must print."""
    directories = path_with() if path is None else path
    result = subprocess.run(
        ["sh", "-c", command],
        cwd=repo.root,
        input=json.dumps(hook_input),
        capture_output=True,
        text=True,
        env={
            **os.environ,
            **UNDER_TEST,
            "CLAUDE_PLUGIN_ROOT": str(PLUGIN),
            "PATH": os.pathsep.join(str(directory) for directory in directories),
        },
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def path_with(*first: Path) -> list[Path | str]:
    return [*first, SCRIPTS, UV.parent, "/usr/bin", "/bin"]


def stop(stop_hook_active: bool = False) -> dict:
    return {"session_id": "session-1", "stop_hook_active": stop_hook_active}


class TestHookConfig:
    def test_claude_code_reviews_when_an_agent_stops(self):
        assert commands(PLUGIN / "hooks" / "hooks.json", "Stop") == [CLAUDE_CODE_COMMAND]

    def test_claude_code_reviews_when_a_subagent_stops(self):
        assert commands(PLUGIN / "hooks" / "hooks.json", "SubagentStop") == [CLAUDE_CODE_COMMAND]

    def test_codex_reviews_when_an_agent_stops(self):
        assert commands(PLUGIN / "hooks" / "codex.json", "Stop") == [CODEX_COMMAND]


@pytest.mark.usefixtures("fake_cli_config", "temporary_home")
class TestStopHook:
    def test_ci_only_rule_does_not_run(self, repo):
        write_package(repo, prefix="rules/")
        repo.write(
            ".codeguard/config.yaml",
            yaml.safe_dump(
                {
                    "packages": [
                        {"kind": "path", "path": "rules", "rulesets": {"python": {"ci_only": True}}}
                    ]
                }
            ),
        )
        (repo.root / ".codeguard/rules/pattern/no-print.yml").unlink()
        repo.write("a.py", "print(1)\n")

        response = run_stop_hook(repo, stop())

        assert response == {}

    def test_error_blocks_a_stop_the_hook_already_blocked(self, repo, make_diagnostic):
        repo.write("a.py", "print(1)\n")

        response = run_stop_hook(repo, stop(stop_hook_active=True))

        assert response == {
            "decision": "block",
            "reason": f"{make_diagnostic()}\n{REQUIRED_FIXES}",
        }

    def test_judge_error_on_an_error_rule_goes_to_the_user(self, repo, make_judge_rule):
        repo.write(".codeguard/rules/judge/placement.md", make_judge_rule().text)
        repo.write(
            ".codeguard/bindings/placement.yaml",
            yaml.safe_dump({"rule": "placement", "paths": ["**/*.py"], "triggers": ["any"]}),
        )
        repo.commit("Bind the rule")
        repo.write("a.py", "x = 1\n")
        configure_fake_cli_response({"stdout": "rate limited\n", "exit_code": 1})

        response = run_stop_hook(repo, stop(), path=path_with(FAKE_CLAUDE.parent))

        assert list(response) == ["systemMessage"]
        assert response["systemMessage"].startswith(
            "codeguard warnings:\na.py: warning placement: The judge call failed"
        )

    def test_claude_code_and_codex_get_the_same_response(self, repo):
        repo.write("a.py", "print(1)\nbreakpoint()\n")

        claude_code = run_stop_hook(repo, stop(), CLAUDE_CODE_COMMAND)
        codex = run_stop_hook(repo, {"session_id": "s", "turn_id": "t"}, CODEX_COMMAND)

        assert claude_code == codex
