from dataclasses import dataclass, field
from pathlib import Path
from threading import Semaphore

from diskcache import Cache

from codeguard.claude_provider import ClaudeJudge, PromptCacheWarmup
from codeguard.codex_provider import CodexJudge
from codeguard.config import ConfigError, JudgeConfig, JudgeModel, JudgeProvider
from codeguard.gemini_provider import BedrockClaude, GeminiJudge, VertexGemini
from codeguard.review import CachedJudge, Deadline, Judge, ReportedDefault

_JUDGEMENT_CACHE_DIR = Path.home() / ".cache" / "codeguard" / "judgements"


@dataclass(frozen=True)
class Judges:
    config: JudgeConfig = JudgeConfig()
    store: Cache = field(default_factory=lambda: Cache(_JUDGEMENT_CACHE_DIR))
    warmup: PromptCacheWarmup = field(default_factory=PromptCacheWarmup)
    processes: dict[JudgeProvider, Semaphore] = field(init=False)
    # What each CLI runs when it's given no model, as its first run reports.
    defaults: dict[JudgeProvider, ReportedDefault] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "processes",
            {provider: Semaphore(self.config.concurrency(provider)) for provider in JudgeProvider},
        )
        object.__setattr__(
            self, "defaults", {provider: ReportedDefault() for provider in JudgeProvider}
        )

    def cached(
        self, root: Path, model: JudgeModel, deadline: Deadline | None = None
    ) -> CachedJudge:
        default = self.defaults[model.provider] if model.name is None else None
        return CachedJudge(self.uncached(root, model, deadline), self.store, root, default=default)

    def uncached(self, root: Path, model: JudgeModel, deadline: Deadline | None = None) -> Judge:
        processes = self.processes[model.provider]
        if model.provider is JudgeProvider.CODEX_CLI:
            return CodexJudge(root, model.name, processes, deadline=deadline)
        if model.provider is JudgeProvider.CLAUDE_CLI:
            return ClaudeJudge(root, model.name, processes, warmup=self.warmup, deadline=deadline)
        if model.name is None:
            raise ConfigError(
                f"provider {model.provider} needs a model: name one in the rule's binding, in "
                "judge.model in .codeguard/config.yaml (or CODEGUARD_JUDGE__MODEL), or in "
                "judge.model in its package's codeguard-package.yaml"
            )
        if model.provider is JudgeProvider.GEMINI:
            models = VertexGemini(self.config.project, self.config.location)
            return GeminiJudge(root, model.name, models, processes, deadline=deadline)
        return GeminiJudge(
            root,
            self.config.bedrock.model_id(model.name),
            BedrockClaude(self.config.bedrock.inference_profile),
            processes,
            deadline=deadline,
            provider=model.provider,
        )
