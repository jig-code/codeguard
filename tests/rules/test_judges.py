from dataclasses import dataclass, field
from pathlib import Path

from diskcache import Cache

from codeguard.claude_provider import ClaudeJudge
from codeguard.codex_provider import CodexJudge
from codeguard.config import BedrockConfig, JudgeConfig, JudgeModel, JudgeProvider
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


def test_bedrock_passes_its_own_model_id_through(tmp_path):
    arn = "arn:aws:bedrock:us-east-1:123456789012:application-inference-profile/haiku"
    model = JudgeModel(provider=JudgeProvider.BEDROCK, name=arn)

    judges = Judges(store=Cache(tmp_path))

    judge = judges.uncached(tmp_path, model)

    assert isinstance(judge, GeminiJudge)
    assert judge.models == BedrockClaude(judges.inference_profiles)
    assert judge.model == arn


@dataclass
class RecordedDefault:
    """A claude default model lookup that records whether each call could probe."""

    model: str | None = "claude-a"
    found_only_by_probe: bool = False
    asked: list[bool] = field(default_factory=list)

    def __call__(self, root: Path, probe: bool) -> str | None:
        self.asked.append(probe)
        return self.model if probe or not self.found_only_by_probe else None


class TestCliDefaultModel:
    def test_claude_default_is_resolved_before_any_judging(self, tmp_path):
        default = RecordedDefault()
        judges = Judges(store=Cache(tmp_path), claude_default_model=default)

        judge = judges.cached(tmp_path, JudgeModel(provider=JudgeProvider.CLAUDE_CLI))

        assert default.asked == [True]
        assert judge.default_model == "claude-a"
        assert judge.cacheable

    def test_claude_default_is_resolved_once_per_run(self, tmp_path):
        default = RecordedDefault()
        judges = Judges(store=Cache(tmp_path), claude_default_model=default)
        model = JudgeModel(provider=JudgeProvider.CLAUDE_CLI)

        judges.cached(tmp_path, model)
        judges.cached(tmp_path, model)

        assert default.asked == [True]

    def test_unknown_claude_default_is_not_cached(self, tmp_path):
        judges = Judges(store=Cache(tmp_path), claude_default_model=RecordedDefault(model=None))

        judge = judges.cached(tmp_path, JudgeModel(provider=JudgeProvider.CLAUDE_CLI))

        assert not judge.cacheable

    def test_dry_run_without_a_probe_asks_again_when_judging(self, tmp_path):
        default = RecordedDefault(found_only_by_probe=True)
        judges = Judges(store=Cache(tmp_path), claude_default_model=default)
        model = JudgeModel(provider=JudgeProvider.CLAUDE_CLI)

        planned = judges.cached(tmp_path, model, probe=False)
        judged = judges.cached(tmp_path, model)

        assert default.asked == [False, True]
        assert not planned.cacheable
        assert judged.default_model == "claude-a"

    def test_codex_without_a_model_is_not_cached(self, tmp_path):
        judges = Judges(store=Cache(tmp_path), claude_default_model=RecordedDefault())

        judge = judges.cached(tmp_path, JudgeModel(provider=JudgeProvider.CODEX_CLI))

        assert not judge.cacheable

    def test_named_model_needs_no_default(self, tmp_path):
        default = RecordedDefault()
        judges = Judges(store=Cache(tmp_path), claude_default_model=default)

        judge = judges.cached(
            tmp_path, JudgeModel(provider=JudgeProvider.CLAUDE_CLI, name="claude-haiku-5-5")
        )

        assert default.asked == []
        assert judge.default_model is None
