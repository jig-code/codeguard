import os
import traceback
from unittest import mock

import pytest
from pydantic import SecretStr

from codeguard.config import (
    ConfigError,
    GeminiSettings,
    JudgeChoice,
    JudgeModel,
    JudgeProvider,
)


class TestGeminiSettings:
    @mock.patch.dict(
        os.environ,
        {
            "CODEGUARD_JUDGE__GEMINI__PROJECT": "my-project",
            "CODEGUARD_JUDGE__GEMINI__LOCATION": "us",
            "CODEGUARD_JUDGE__GEMINI__API_KEY": "proxy-injected",
        },
    )
    def test_settings_come_from_the_environment(self):
        assert GeminiSettings() == GeminiSettings(
            project="my-project", location="us", api_key=SecretStr("proxy-injected")
        )

    def test_models_without_gemini_need_no_sign_in(self):
        models = [
            JudgeModel(provider=JudgeProvider.CLAUDE_CLI),
            JudgeModel(provider=JudgeProvider.CODEX_CLI, name="gpt-6-luna"),
            JudgeModel(provider=JudgeProvider.BEDROCK, name="us.anthropic.claude-haiku-5-5"),
        ]

        GeminiSettings().require_sign_in_for(models)

    def test_gemini_model_without_a_project_is_a_config_error(self, tmp_path):
        settings = GeminiSettings(credentials_file=tmp_path / "judge.json")
        model = JudgeModel(provider=JudgeProvider.GEMINI, name="gemini-judge-test")

        with pytest.raises(ConfigError) as error:
            settings.require_sign_in_for([model])

        assert str(error.value) == "Gemini needs a project: set CODEGUARD_JUDGE__GEMINI__PROJECT"

    def test_gemini_model_without_a_sign_in_is_a_config_error(self):
        model = JudgeModel(provider=JudgeProvider.GEMINI, name="gemini-judge-test")

        with pytest.raises(ConfigError) as error:
            GeminiSettings(project="sanctum").require_sign_in_for([model])

        assert str(error.value) == (
            "Gemini needs a way to sign in: set CODEGUARD_JUDGE__GEMINI__API_KEY or "
            "CODEGUARD_JUDGE__GEMINI__CREDENTIALS_FILE"
        )

    def test_two_sign_ins_are_a_config_error_that_leaves_out_the_key(self, tmp_path):
        settings = GeminiSettings(
            project="sanctum",
            api_key=SecretStr("secret-key-value"),
            credentials_file=tmp_path / "judge.json",
        )
        model = JudgeModel(provider=JudgeProvider.GEMINI, name="gemini-judge-test")

        with pytest.raises(ConfigError) as error:
            settings.require_sign_in_for([model])

        assert str(error.value) == (
            "Gemini needs one way to sign in: set CODEGUARD_JUDGE__GEMINI__API_KEY or "
            "CODEGUARD_JUDGE__GEMINI__CREDENTIALS_FILE, not both"
        )
        assert "secret-key-value" not in "".join(traceback.format_exception(error.value))


class TestJudgeChoice:
    def test_provider_without_a_model_judges_with_its_default_model(self):
        assert JudgeChoice.of_provider(JudgeProvider.GEMINI) == JudgeChoice(
            provider=JudgeProvider.GEMINI, model=JudgeProvider.GEMINI.default_model
        )

    def test_given_model_replaces_the_provider_s_default(self):
        assert JudgeChoice.of_provider(JudgeProvider.GEMINI, "gemini-judge-test") == JudgeChoice(
            provider=JudgeProvider.GEMINI, model="gemini-judge-test"
        )

    def test_claude_cli_without_a_model_leaves_the_model_to_the_cli(self):
        assert JudgeChoice.of_provider(JudgeProvider.CLAUDE_CLI) == JudgeChoice(
            provider=JudgeProvider.CLAUDE_CLI
        )
