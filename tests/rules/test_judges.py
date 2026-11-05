import pytest
from diskcache import Cache

from codeguard.claude_provider import ClaudeJudge
from codeguard.codex_provider import CodexJudge
from codeguard.config import BedrockConfig, ConfigError, JudgeConfig, JudgeModel, JudgeProvider
from codeguard.gemini_provider import BedrockClaude, GeminiJudge
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

    def test_gemini_model_builds_a_gemini_judge_with_its_name(self, tmp_path):
        judges = Judges(JudgeConfig(project="sanctum"), store=Cache(tmp_path))
        model = JudgeModel(provider=JudgeProvider.GEMINI, name="gemini-3.1-pro-preview")

        judge = judges.uncached(tmp_path, model)

        assert isinstance(judge, GeminiJudge)
        assert judge.model == "gemini-3.1-pro-preview"
        assert judge.processes is judges.processes[JudgeProvider.GEMINI]

    def test_bedrock_model_builds_a_judge_cached_apart_from_gemini(self, tmp_path):
        judges = Judges(store=Cache(tmp_path))
        model = JudgeModel(provider=JudgeProvider.BEDROCK, name="claude-haiku-5-5")

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


def test_bedrock_names_a_gpt_model_by_its_openai_profile(tmp_path):
    judges = Judges(store=Cache(tmp_path))
    model = JudgeModel(provider=JudgeProvider.BEDROCK, name="gpt-6-luna")

    judge = judges.uncached(tmp_path, model)

    assert isinstance(judge, GeminiJudge)
    assert judge.identity == "bedrock\0us.openai.gpt-6-luna"


def test_bedrock_profile_takes_the_configured_prefix(tmp_path):
    config = JudgeConfig(bedrock=BedrockConfig(inference_prefix="eu"))
    model = JudgeModel(provider=JudgeProvider.BEDROCK, name="claude-haiku-5-5")

    judge = Judges(config, store=Cache(tmp_path)).uncached(tmp_path, model)

    assert isinstance(judge, GeminiJudge)
    assert judge.model == "eu.anthropic.claude-haiku-5-5"


def test_bedrock_routes_through_the_configured_application_profile(tmp_path):
    arn = "arn:aws:bedrock:us-east-1:123456789012:application-inference-profile/haiku"
    config = JudgeConfig(bedrock=BedrockConfig(inference_profile=arn))
    model = JudgeModel(provider=JudgeProvider.BEDROCK, name="claude-haiku-5-5")

    judge = Judges(config, store=Cache(tmp_path)).uncached(tmp_path, model)

    assert isinstance(judge, GeminiJudge)
    assert judge.models == BedrockClaude(arn)
    assert judge.model == "us.anthropic.claude-haiku-5-5"


def test_bedrock_model_of_another_vendor_is_an_error(tmp_path):
    model = JudgeModel(provider=JudgeProvider.BEDROCK, name="gemini-3.1-pro-preview")

    with pytest.raises(ConfigError) as error:
        Judges(store=Cache(tmp_path)).uncached(tmp_path, model)

    assert str(error.value) == "bedrock runs Claude and GPT models, not gemini-3.1-pro-preview"


@pytest.mark.parametrize("provider", [JudgeProvider.CLAUDE_CLI, JudgeProvider.CODEX_CLI])
def test_cli_judge_without_a_model_runs_the_cli_default(tmp_path, provider):
    judge = Judges(store=Cache(tmp_path)).uncached(tmp_path, JudgeModel(provider=provider))

    assert isinstance(judge, ClaudeJudge | CodexJudge)
    assert judge.model is None


@pytest.mark.parametrize("provider", [JudgeProvider.GEMINI, JudgeProvider.BEDROCK])
def test_api_judge_without_a_model_is_an_error(tmp_path, provider):
    judges = Judges(store=Cache(tmp_path))

    with pytest.raises(ConfigError) as error:
        judges.uncached(tmp_path, JudgeModel(provider=provider))

    assert str(error.value) == (
        f"provider {provider} needs a model: name one in the rule's binding, in judge.model in "
        ".codeguard/config.yaml (or CODEGUARD_JUDGE__MODEL), or in judge.model in its "
        "package's codeguard-package.yaml"
    )
