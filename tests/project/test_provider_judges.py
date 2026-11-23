from pydantic import SecretStr

from codeguard.api_provider import ApiJudge, BedrockClaude, VertexGemini
from codeguard.claude_provider import ClaudeJudge
from codeguard.codex_provider import CodexJudge
from codeguard.config import (
    GeminiSettings,
    JudgeConfig,
    JudgeModel,
    JudgeProvider,
)
from codeguard.project import ProviderJudges


class TestProviderJudges:
    def test_every_claude_judge_shares_the_process_limit_and_warmup(self, tmp_path):
        judges = ProviderJudges()

        sonnet = judges(tmp_path, JudgeModel(provider=JudgeProvider.CLAUDE_CLI, name="sonnet"))
        opus = judges(tmp_path, JudgeModel(provider=JudgeProvider.CLAUDE_CLI, name="opus"))

        assert isinstance(sonnet, ClaudeJudge)
        assert isinstance(opus, ClaudeJudge)
        assert sonnet.processes is opus.processes is judges.processes[JudgeProvider.CLAUDE_CLI]
        assert sonnet.warmup is opus.warmup is judges.warmup

    def test_gemini_judge_runs_with_the_gemini_settings(self, tmp_path):
        settings = GeminiSettings(
            project="sanctum", location="eu", api_key=SecretStr("proxy-injected")
        )
        judges = ProviderJudges(gemini=settings)
        model = JudgeModel(provider=JudgeProvider.GEMINI, name="gemini-judge-test")

        judge = judges(tmp_path, model)

        assert judge == ApiJudge(
            tmp_path,
            "gemini-judge-test",
            VertexGemini("sanctum", "eu", SecretStr("proxy-injected")),
            judges.processes[JudgeProvider.GEMINI],
            JudgeProvider.GEMINI,
            "medium",
            judges.config.request_time_limit_seconds,
        )

    def test_bedrock_model_builds_a_judge_cached_apart_from_gemini(self, tmp_path):
        judges = ProviderJudges()
        model = JudgeModel(provider=JudgeProvider.BEDROCK, name="us.anthropic.claude-haiku-5-5")

        judge = judges(tmp_path, model)

        assert isinstance(judge, ApiJudge)
        assert judge.identity == ("bedrock\0us.anthropic.claude-haiku-5-5\0thinking=medium")
        assert judge.processes is judges.processes[JudgeProvider.BEDROCK]


def test_codex_binding_builds_a_separate_subscription_judge(tmp_path):
    judges = ProviderJudges()
    model = JudgeModel(provider=JudgeProvider.CODEX_CLI, name="gpt-6-luna")

    judge = judges(tmp_path, model)

    assert isinstance(judge, CodexJudge)
    assert judge.model == model.name
    assert judge.processes is judges.processes[JudgeProvider.CODEX_CLI]
    assert (
        judge.identity
        != judges(tmp_path, JudgeModel(provider=JudgeProvider.BEDROCK, name=model.name)).identity
    )


def test_bedrock_accepts_a_gpt_inference_profile_without_changing_the_backend(tmp_path):
    judges = ProviderJudges()
    model = JudgeModel(provider=JudgeProvider.BEDROCK, name="us.openai.gpt-6-luna")

    judge = judges(tmp_path, model)

    assert isinstance(judge, ApiJudge)
    assert judge.identity == "bedrock\0us.openai.gpt-6-luna\0thinking=medium"


class TestJudgeThinking:
    def test_claude_judge_runs_at_the_claude_cli_level(self, tmp_path):
        config = JudgeConfig.model_validate({"thinking": {"claude-cli": "xhigh"}})
        judges = ProviderJudges(config)

        judge = judges(tmp_path, JudgeModel(provider=JudgeProvider.CLAUDE_CLI))

        assert judge == ClaudeJudge(
            tmp_path,
            None,
            judges.processes[JudgeProvider.CLAUDE_CLI],
            warmup=judges.warmup,
            thinking="xhigh",
        )

    def test_codex_judge_runs_at_the_codex_cli_level(self, tmp_path):
        config = JudgeConfig.model_validate({"thinking": {"codex-cli": "low"}})
        judges = ProviderJudges(config)

        judge = judges(tmp_path, JudgeModel(provider=JudgeProvider.CODEX_CLI, name="gpt-6-luna"))

        assert judge == CodexJudge(
            tmp_path, "gpt-6-luna", judges.processes[JudgeProvider.CODEX_CLI], thinking="low"
        )

    def test_api_judge_runs_with_the_request_time_limit(self, tmp_path):
        judges = ProviderJudges(JudgeConfig(request_time_limit_seconds=180))

        judge = judges(
            tmp_path,
            JudgeModel(provider=JudgeProvider.BEDROCK, name="us.anthropic.claude-haiku-5-5"),
        )

        assert judge == ApiJudge(
            tmp_path,
            "us.anthropic.claude-haiku-5-5",
            BedrockClaude(),
            judges.processes[JudgeProvider.BEDROCK],
            JudgeProvider.BEDROCK,
            "medium",
            180,
        )

    def test_bedrock_judge_runs_at_the_bedrock_level(self, tmp_path):
        config = JudgeConfig.model_validate({"thinking": {"bedrock": "max"}})
        judges = ProviderJudges(config)

        judge = judges(
            tmp_path,
            JudgeModel(provider=JudgeProvider.BEDROCK, name="us.anthropic.claude-haiku-5-5"),
        )

        assert judge == ApiJudge(
            tmp_path,
            "us.anthropic.claude-haiku-5-5",
            BedrockClaude(),
            judges.processes[JudgeProvider.BEDROCK],
            JudgeProvider.BEDROCK,
            "max",
            judges.config.request_time_limit_seconds,
        )

    def test_default_gives_a_cli_judge_no_level(self, tmp_path):
        config = JudgeConfig.model_validate({"thinking": {"claude-cli": "default"}})
        judges = ProviderJudges(config)

        judge = judges(tmp_path, JudgeModel(provider=JudgeProvider.CLAUDE_CLI))

        assert judge == ClaudeJudge(
            tmp_path, None, judges.processes[JudgeProvider.CLAUDE_CLI], warmup=judges.warmup
        )

    def test_default_gives_an_api_judge_no_level(self, tmp_path):
        settings = GeminiSettings(project="a-project", api_key=SecretStr("proxy-injected"))
        config = JudgeConfig.model_validate({"thinking": {"gemini": "default"}})
        judges = ProviderJudges(config, settings)

        judge = judges(
            tmp_path, JudgeModel(provider=JudgeProvider.GEMINI, name="gemini-judge-test")
        )

        assert judge == ApiJudge(
            tmp_path,
            "gemini-judge-test",
            VertexGemini("a-project", "global", SecretStr("proxy-injected")),
            judges.processes[JudgeProvider.GEMINI],
            JudgeProvider.GEMINI,
            None,
            judges.config.request_time_limit_seconds,
        )
