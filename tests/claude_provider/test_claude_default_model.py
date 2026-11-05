import json

import pytest
from claude_output import claude_stream
from fake_cli import FAKE_CLAUDE, configure_fake_cli_response

from codeguard.claude_provider import ClaudeDefaultModel

pytestmark = pytest.mark.usefixtures("fake_cli_config")


@pytest.fixture
def calls(tmp_path):
    return tmp_path / "calls"


def default_model(tmp_path, environment=None) -> ClaudeDefaultModel:
    (tmp_path / "home").mkdir(exist_ok=True)
    return ClaudeDefaultModel(
        tmp_path,
        executable=str(FAKE_CLAUDE),
        environment=environment or {},
        home=tmp_path / "home",
        managed_settings=(),
    )


def write_settings(path, settings: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings))


def answer(calls, stream: str, exit_code: int = 0) -> None:
    configure_fake_cli_response({"stdout": stream, "calls": str(calls), "exit_code": exit_code})


class TestClaudeDefaultModel:
    def test_model_variable_names_it_without_asking_the_cli(self, tmp_path, calls):
        answer(calls, claude_stream([], model="claude-other"))
        lookup = default_model(tmp_path, {"ANTHROPIC_MODEL": "claude-opus-5-5"})

        assert lookup.resolve() == "claude-opus-5-5"
        assert not calls.exists()

    def test_project_settings_name_it_without_asking_the_cli(self, tmp_path, calls):
        answer(calls, claude_stream([], model="claude-other"))
        write_settings(tmp_path / ".claude/settings.json", {"model": "claude-haiku-5-5"})

        assert default_model(tmp_path).resolve() == "claude-haiku-5-5"
        assert not calls.exists()

    def test_model_variable_wins_over_settings(self, tmp_path):
        write_settings(tmp_path / ".claude/settings.json", {"model": "claude-haiku-5-5"})
        lookup = default_model(tmp_path, {"ANTHROPIC_MODEL": "claude-opus-5-5"})

        assert lookup.configured() == "claude-opus-5-5"

    def test_local_settings_win_over_project_and_user_settings(self, tmp_path):
        write_settings(tmp_path / "home/.claude/settings.json", {"model": "claude-user"})
        write_settings(tmp_path / ".claude/settings.json", {"model": "claude-project"})
        write_settings(tmp_path / ".claude/settings.local.json", {"model": "claude-local"})

        assert default_model(tmp_path).configured() == "claude-local"

    def test_settings_env_wins_over_a_settings_model(self, tmp_path):
        write_settings(tmp_path / ".claude/settings.local.json", {"model": "claude-local"})
        write_settings(
            tmp_path / "home/.claude/settings.json",
            {"env": {"ANTHROPIC_MODEL": "claude-from-env"}},
        )

        assert default_model(tmp_path).configured() == "claude-from-env"

    def test_managed_settings_win_over_every_other_file(self, tmp_path):
        managed = tmp_path / "managed/managed-settings.json"
        write_settings(managed, {"model": "claude-managed"})
        write_settings(tmp_path / ".claude/settings.local.json", {"model": "claude-local"})
        lookup = ClaudeDefaultModel(
            tmp_path, environment={}, home=tmp_path / "home", managed_settings=(managed,)
        )

        assert lookup.configured() == "claude-managed"

    def test_alias_in_settings_asks_the_cli(self, tmp_path, calls):
        answer(calls, claude_stream([], model="claude-opus-5-5"))
        write_settings(tmp_path / ".claude/settings.json", {"model": "opus"})

        assert default_model(tmp_path).resolve() == "claude-opus-5-5"
        assert calls.read_text() == "called\n"

    def test_cli_reports_the_model_its_init_message_names(self, tmp_path, calls):
        init = json.dumps({"type": "system", "subtype": "init", "model": "claude-fable-5-1"})
        answer(calls, f"{init}\n{claude_stream([], model='claude-other')}")

        assert default_model(tmp_path).resolve() == "claude-fable-5-1"

    def test_without_a_probe_nothing_named_is_unknown(self, tmp_path, calls):
        answer(calls, claude_stream([], model="claude-opus-5-5"))

        assert default_model(tmp_path).resolve(probe=False) is None
        assert not calls.exists()

    def test_failed_call_leaves_it_unknown(self, tmp_path, calls):
        answer(calls, "rate limited\n", exit_code=1)

        assert default_model(tmp_path).resolve() is None
