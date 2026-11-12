import os
from unittest import mock

from diskcache import Cache

from codeguard.claude_provider import ClaudeJudge
from codeguard.codex_provider import CodexJudge
from codeguard.config import JudgeConfig, JudgeModel, JudgeProvider
from codeguard.gemini_provider import BedrockClaude, GeminiJudge, VertexGemini
from codeguard.review import CachedJudge
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

        processes = judges.processes[JudgeProvider.CLAUDE_CLI]
        assert cached == CachedJudge(
            ClaudeJudge(tmp_path, "sonnet", processes, warmup=judges.warmup),
            judges.store,
            tmp_path,
        )
        assert uncached == ClaudeJudge(tmp_path, "opus", processes, warmup=judges.warmup)

    @mock.patch.dict(os.environ, {"GOOGLE_API_KEY": "proxy-injected"})
    def test_gemini_judge_runs_in_the_configured_project_and_location(self, tmp_path):
        judges = Judges(JudgeConfig(project="sanctum", location="eu"), store=Cache(tmp_path))
        model = JudgeModel(provider=JudgeProvider.GEMINI, name="gemini-4-argon")

        judge = judges.uncached(tmp_path, model)

        assert judge == GeminiJudge(
            tmp_path,
            "gemini-4-argon",
            VertexGemini(project="sanctum", location="eu", api_key="proxy-injected"),
            judges.processes[JudgeProvider.GEMINI],
        )

    def test_bedrock_model_builds_a_judge_cached_apart_from_gemini(self, tmp_path):
        judges = Judges(store=Cache(tmp_path))
        model = JudgeModel(provider=JudgeProvider.BEDROCK, name="us.anthropic.claude-haiku-5-5")

        judge = judges.uncached(tmp_path, model)

        assert judge == GeminiJudge(
            tmp_path,
            "us.anthropic.claude-haiku-5-5",
            BedrockClaude(),
            judges.processes[JudgeProvider.BEDROCK],
            provider=JudgeProvider.BEDROCK,
        )


def test_codex_binding_builds_a_separate_subscription_judge(tmp_path):
    judges = Judges(store=Cache(tmp_path))
    model = JudgeModel(provider=JudgeProvider.CODEX_CLI, name="gpt-6-luna")

    judge = judges.uncached(tmp_path, model)

    assert judge == CodexJudge(tmp_path, "gpt-6-luna", judges.processes[JudgeProvider.CODEX_CLI])
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

    assert judge == GeminiJudge(
        tmp_path,
        "us.openai.gpt-6-luna",
        BedrockClaude(),
        judges.processes[JudgeProvider.BEDROCK],
        provider=JudgeProvider.BEDROCK,
    )
