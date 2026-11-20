from collections.abc import Iterable
from dataclasses import dataclass, field
from os import process_cpu_count
from pathlib import Path
from threading import Semaphore

from diskcache import Cache

from codeguard.claude_provider import ClaudeJudge, PromptCacheWarmup
from codeguard.codex_provider import CodexJudge
from codeguard.config import GeminiSettings, JudgeConfig, JudgeModel, JudgeProvider
from codeguard.gemini_provider import BedrockClaude, GeminiJudge, VertexGemini, require_ripgrep
from codeguard.review import CachedJudge, Deadline, Judge

_JUDGEMENT_CACHE_DIR = Path.home() / ".cache" / "codeguard" / "judgements"


@dataclass(frozen=True)
class Judges:
    config: JudgeConfig = JudgeConfig()
    gemini: GeminiSettings = field(default_factory=GeminiSettings)
    store: Cache = field(default_factory=lambda: Cache(_JUDGEMENT_CACHE_DIR))
    warmup: PromptCacheWarmup = field(default_factory=PromptCacheWarmup)
    processes: dict[JudgeProvider, Semaphore] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "processes",
            {
                provider: Semaphore(self.config.concurrency(provider, process_cpu_count()))
                for provider in JudgeProvider
            },
        )

    def require_setup(self, models: Iterable[JudgeModel]) -> None:
        """Fail before judging when a judge the models need can't run."""
        providers = {model.provider for model in models}
        if JudgeProvider.GEMINI in providers:
            self.gemini.check_sign_in()
        for provider in sorted(providers):
            if not provider.runs_a_cli:
                require_ripgrep(provider)

    def cached(
        self, root: Path, model: JudgeModel, deadline: Deadline | None = None
    ) -> CachedJudge:
        return CachedJudge(self.uncached(root, model, deadline), self.store, root)

    def uncached(self, root: Path, model: JudgeModel, deadline: Deadline | None = None) -> Judge:
        processes = self.processes[model.provider]
        if model.provider is JudgeProvider.CODEX_CLI:
            return CodexJudge(root, model.required_name, processes, deadline=deadline)
        if model.provider is JudgeProvider.GEMINI:
            gemini = self.gemini
            models = VertexGemini(
                gemini.project, gemini.location, gemini.api_key, gemini.credentials_file
            )
            return GeminiJudge(root, model.required_name, models, processes, deadline=deadline)
        if model.provider is JudgeProvider.BEDROCK:
            return GeminiJudge(
                root,
                model.required_name,
                BedrockClaude(),
                processes,
                deadline=deadline,
                provider=model.provider,
            )
        return ClaudeJudge(root, model.name, processes, warmup=self.warmup, deadline=deadline)
