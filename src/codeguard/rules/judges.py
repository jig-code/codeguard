from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock, Semaphore

from diskcache import Cache

from codeguard.claude_provider import ClaudeDefaultModel, ClaudeJudge, PromptCacheWarmup
from codeguard.codex_provider import CodexJudge
from codeguard.config import ConfigError, JudgeConfig, JudgeModel, JudgeProvider
from codeguard.gemini_provider import (
    BedrockClaude,
    GeminiJudge,
    InferenceProfileModels,
    VertexGemini,
)
from codeguard.review import CachedJudge, Deadline, Judge

_JUDGEMENT_CACHE_DIR = Path.home() / ".cache" / "codeguard" / "judgements"


def _claude_default_model(root: Path, probe: bool) -> str | None:
    return ClaudeDefaultModel(root).resolve(probe)


@dataclass(frozen=True)
class Judges:
    config: JudgeConfig = JudgeConfig()
    store: Cache = field(default_factory=lambda: Cache(_JUDGEMENT_CACHE_DIR))
    warmup: PromptCacheWarmup = field(default_factory=PromptCacheWarmup)
    # The model the claude CLI runs when it's given none, given whether it may be asked.
    claude_default_model: Callable[[Path, bool], str | None] = _claude_default_model
    # The model each Bedrock application inference profile routes to, read once per profile.
    inference_profiles: InferenceProfileModels = field(default_factory=InferenceProfileModels)
    processes: dict[JudgeProvider, Semaphore] = field(init=False)
    default_models: dict[JudgeProvider, str | None] = field(init=False, default_factory=dict)
    default_models_lock: Lock = field(init=False, default_factory=Lock)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "processes",
            {provider: Semaphore(self.config.concurrency(provider)) for provider in JudgeProvider},
        )

    def cached(
        self,
        root: Path,
        model: JudgeModel,
        deadline: Deadline | None = None,
        probe: bool = True,
    ) -> CachedJudge:
        """The judge, its verdicts cached under its model. A judge that names no model is
        keyed on the model its CLI runs by default, found before any judging; `probe` lets
        that ask the CLI, which costs a model call. Its verdicts aren't cached when the
        model can't be told."""
        judge = self.uncached(root, model, deadline)
        if model.name is not None:
            return CachedJudge(judge, self.store, root)
        default = self._default_model(root, model.provider, probe)
        return CachedJudge(
            judge, self.store, root, default_model=default, cacheable=default is not None
        )

    def _default_model(self, root: Path, provider: JudgeProvider, probe: bool) -> str | None:
        # The codex CLI doesn't tell which model it runs by default.
        if provider is not JudgeProvider.CLAUDE_CLI:
            return None
        with self.default_models_lock:
            if provider in self.default_models:
                return self.default_models[provider]
            default = self.claude_default_model(root, probe)
            if default is not None or probe:
                self.default_models[provider] = default
            return default

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
            BedrockClaude(self.inference_profiles),
            processes,
            deadline=deadline,
            provider=model.provider,
        )
