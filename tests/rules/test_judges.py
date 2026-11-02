from diskcache import Cache

from codeguard.claude_provider import ClaudeJudge
from codeguard.config import JudgeConfig, JudgeModel, JudgeProvider
from codeguard.gemini_provider import GeminiJudge
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
        model = JudgeModel(provider=JudgeProvider.BEDROCK, name="us.anthropic.claude-haiku-5-5")

        judge = judges.uncached(tmp_path, model)

        assert isinstance(judge, GeminiJudge)
        assert judge.identity == "bedrock\0us.anthropic.claude-haiku-5-5"
        assert judge.processes is judges.processes[JudgeProvider.BEDROCK]
