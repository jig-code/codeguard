import pytest
from diskcache import Cache
from pydantic import SecretStr

from codeguard.claude_provider import ClaudeJudge
from codeguard.codex_provider import CodexJudge
from codeguard.config import ConfigError, GeminiSettings, JudgeModel, JudgeProvider
from codeguard.gemini_provider import GeminiJudge, VertexGemini
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

        assert judge == GeminiJudge(
            tmp_path,
            "gemini-judge-test",
            VertexGemini(settings),
            judges.processes[JudgeProvider.GEMINI],
        )

    def test_gemini_with_a_key_file_and_no_project_is_a_config_error(self, tmp_path):
        settings = GeminiSettings(credentials_file=tmp_path / "judge.json")
        judges = Judges(gemini=settings, store=Cache(tmp_path))
        model = JudgeModel(provider=JudgeProvider.GEMINI, name="gemini-judge-test")

        with pytest.raises(ConfigError) as error:
            judges.check_sign_ins([model])

        assert str(error.value) == "Gemini needs a project: set CODEGUARD_JUDGE__GEMINI__PROJECT"

    def test_gemini_without_a_sign_in_is_a_config_error(self, tmp_path):
        judges = Judges(gemini=GeminiSettings(project="sanctum"), store=Cache(tmp_path))
        model = JudgeModel(provider=JudgeProvider.GEMINI, name="gemini-judge-test")

        with pytest.raises(ConfigError) as error:
            judges.check_sign_ins([model])

        assert str(error.value) == (
            "Gemini needs a way to sign in: set CODEGUARD_JUDGE__GEMINI__API_KEY or "
            "CODEGUARD_JUDGE__GEMINI__CREDENTIALS_FILE"
        )

    def test_bedrock_model_builds_a_judge_cached_apart_from_gemini(self, tmp_path):
        judges = Judges(store=Cache(tmp_path))
        model = JudgeModel(provider=JudgeProvider.BEDROCK, name="us.anthropic.claude-haiku-5-5")

        judge = judges.uncached(tmp_path, model)

        assert isinstance(judge, GeminiJudge)
        assert judge.identity == "bedrock\0us.anthropic.claude-haiku-5-5"
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

    assert isinstance(judge, GeminiJudge)
    assert judge.identity == "bedrock\0us.openai.gpt-6-luna"
