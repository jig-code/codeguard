import os
import traceback
from unittest import mock

import pytest
from diskcache import Cache
from pydantic import SecretStr

from codeguard.api_provider import ApiJudge, VertexGemini
from codeguard.claude_provider import ClaudeJudge
from codeguard.codex_provider import CodexJudge
from codeguard.config import (
    ConfigError,
    GeminiSettings,
    JudgeConfig,
    JudgeModel,
    JudgeProvider,
)
from codeguard.rules.judges import Judges


class TestJudges:
    def test_every_judge_shares_the_store_process_limit_and_warmup(self, tmp_path):
        judges = Judges(store=Cache(tmp_path))

        cached = judges.cached(
            tmp_path, JudgeModel(provider=JudgeProvider.CLAUDE_CLI, name="sonnet")
        )
        uncached = judges.uncached(
            tmp_path, JudgeModel(provider=JudgeProvider.CLAUDE_CLI, name="opus")
        )

        assert isinstance(cached.wrapped, ClaudeJudge)
        assert isinstance(uncached, ClaudeJudge)
        assert cached.store is judges.store
        assert cached.wrapped.processes is uncached.processes
        assert uncached.processes is judges.processes[JudgeProvider.CLAUDE_CLI]
        assert cached.wrapped.warmup is uncached.warmup is judges.warmup

    def test_gemini_judge_runs_with_the_gemini_settings(self, tmp_path):
        settings = GeminiSettings(
            project="sanctum", location="eu", api_key=SecretStr("proxy-injected")
        )
        judges = Judges(gemini=settings, store=Cache(tmp_path))
        model = JudgeModel(provider=JudgeProvider.GEMINI, name="gemini-judge-test")

        judge = judges.uncached(tmp_path, model)

        assert judge == ApiJudge(
            tmp_path,
            "gemini-judge-test",
            VertexGemini("sanctum", "eu", SecretStr("proxy-injected")),
            judges.processes[JudgeProvider.GEMINI],
            JudgeProvider.GEMINI,
            "medium",
        )

    @mock.patch.dict(
        os.environ,
        {
            "CODEGUARD_JUDGE__GEMINI__PROJECT": "my-project",
            "CODEGUARD_JUDGE__GEMINI__LOCATION": "us",
            "CODEGUARD_JUDGE__GEMINI__API_KEY": "proxy-injected",
        },
    )
    def test_gemini_settings_come_from_the_environment(self, tmp_path):
        judges = Judges(store=Cache(tmp_path))

        assert judges.gemini == GeminiSettings(
            project="my-project", location="us", api_key=SecretStr("proxy-injected")
        )

    def test_gemini_with_a_key_file_and_no_project_is_a_config_error(self, tmp_path):
        settings = GeminiSettings(credentials_file=tmp_path / "judge.json")
        judges = Judges(gemini=settings, store=Cache(tmp_path))
        model = JudgeModel(provider=JudgeProvider.GEMINI, name="gemini-judge-test")

        with pytest.raises(ConfigError) as error:
            judges.require_sign_ins([model])

        assert str(error.value) == "Gemini needs a project: set CODEGUARD_JUDGE__GEMINI__PROJECT"

    def test_gemini_without_a_sign_in_is_a_config_error(self, tmp_path):
        judges = Judges(gemini=GeminiSettings(project="sanctum"), store=Cache(tmp_path))
        model = JudgeModel(provider=JudgeProvider.GEMINI, name="gemini-judge-test")

        with pytest.raises(ConfigError) as error:
            judges.require_sign_ins([model])

        assert str(error.value) == (
            "Gemini needs a way to sign in: set CODEGUARD_JUDGE__GEMINI__API_KEY or "
            "CODEGUARD_JUDGE__GEMINI__CREDENTIALS_FILE"
        )

    def test_two_gemini_sign_ins_are_a_config_error_that_leaves_out_the_key(self, tmp_path):
        settings = GeminiSettings(
            project="sanctum",
            api_key=SecretStr("secret-key-value"),
            credentials_file=tmp_path / "judge.json",
        )
        judges = Judges(gemini=settings, store=Cache(tmp_path))
        model = JudgeModel(provider=JudgeProvider.GEMINI, name="gemini-judge-test")

        with pytest.raises(ConfigError) as error:
            judges.require_sign_ins([model])

        assert str(error.value) == (
            "Gemini needs one way to sign in: set CODEGUARD_JUDGE__GEMINI__API_KEY or "
            "CODEGUARD_JUDGE__GEMINI__CREDENTIALS_FILE, not both"
        )
        assert "secret-key-value" not in "".join(traceback.format_exception(error.value))

    def test_bedrock_model_builds_a_judge_cached_apart_from_gemini(self, tmp_path):
        judges = Judges(store=Cache(tmp_path))
        model = JudgeModel(provider=JudgeProvider.BEDROCK, name="us.anthropic.claude-haiku-5-5")

        judge = judges.uncached(tmp_path, model)

        assert isinstance(judge, ApiJudge)
        assert judge.identity == ("bedrock\0us.anthropic.claude-haiku-5-5\0thinking=medium")
        assert judge.processes is judges.processes[JudgeProvider.BEDROCK]


def test_codex_binding_builds_a_separate_subscription_judge(tmp_path):
    judges = Judges(store=Cache(tmp_path))
    model = JudgeModel(provider=JudgeProvider.CODEX_CLI, name="gpt-6-luna")

    judge = judges.uncached(tmp_path, model)

    assert isinstance(judge, CodexJudge)
    assert judge.model == model.name
    assert judge.processes is judges.processes[JudgeProvider.CODEX_CLI]
    assert (
        judge.identity
        != judges.uncached(
            tmp_path, JudgeModel(provider=JudgeProvider.BEDROCK, name=model.name)
        ).identity
    )


def test_bedrock_accepts_a_gpt_inference_profile_without_changing_the_backend(tmp_path):
    judges = Judges(store=Cache(tmp_path))
    model = JudgeModel(provider=JudgeProvider.BEDROCK, name="us.openai.gpt-6-luna")

    judge = judges.uncached(tmp_path, model)

    assert isinstance(judge, ApiJudge)
    assert judge.identity == "bedrock\0us.openai.gpt-6-luna\0thinking=medium"


class TestJudgeThinking:
    @pytest.mark.parametrize(
        ("provider", "name"),
        [
            (JudgeProvider.GEMINI, "gemini-judge-test"),
            (JudgeProvider.BEDROCK, "us.anthropic.claude-haiku-5-5"),
        ],
    )
    def test_an_api_judge_thinks_at_medium_by_default(self, tmp_path, provider, name):
        judge = Judges(store=Cache(tmp_path)).uncached(
            tmp_path, JudgeModel(provider=provider, name=name)
        )

        assert isinstance(judge, ApiJudge)
        assert judge.thinking == "medium"

    @pytest.mark.parametrize(
        ("provider", "name"),
        [(JudgeProvider.CLAUDE_CLI, None), (JudgeProvider.CODEX_CLI, "gpt-6-luna")],
    )
    def test_a_cli_judge_runs_at_the_cli_default_by_default(self, tmp_path, provider, name):
        judge = Judges(store=Cache(tmp_path)).uncached(
            tmp_path, JudgeModel(provider=provider, name=name)
        )

        assert isinstance(judge, ClaudeJudge | CodexJudge)
        assert judge.thinking is None

    @pytest.mark.parametrize(
        ("provider", "name"),
        [
            (JudgeProvider.CLAUDE_CLI, None),
            (JudgeProvider.CODEX_CLI, "gpt-6-luna"),
            (JudgeProvider.GEMINI, "gemini-judge-test"),
            (JudgeProvider.BEDROCK, "us.anthropic.claude-haiku-5-5"),
        ],
    )
    def test_each_provider_thinks_at_the_level_the_project_sets_for_it(
        self, tmp_path, provider, name
    ):
        config = JudgeConfig.model_validate({"thinking": {str(provider): "high"}})
        judges = Judges(config, store=Cache(tmp_path))

        judge = judges.uncached(tmp_path, JudgeModel(provider=provider, name=name))

        assert isinstance(judge, ApiJudge | ClaudeJudge | CodexJudge)
        assert judge.thinking == "high"

    def test_a_level_set_for_one_provider_leaves_the_others_at_their_default(self, tmp_path):
        config = JudgeConfig.model_validate({"thinking": {"gemini": "low"}})
        judges = Judges(config, store=Cache(tmp_path))

        bedrock = judges.uncached(
            tmp_path,
            JudgeModel(provider=JudgeProvider.BEDROCK, name="us.anthropic.claude-haiku-5-5"),
        )
        claude = judges.uncached(tmp_path, JudgeModel(provider=JudgeProvider.CLAUDE_CLI))

        assert isinstance(bedrock, ApiJudge)
        assert isinstance(claude, ClaudeJudge)
        assert bedrock.thinking == "medium"
        assert claude.thinking is None
