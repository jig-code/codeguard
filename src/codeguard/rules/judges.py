from dataclasses import dataclass, field
from os import environ, process_cpu_count
from pathlib import Path
from threading import Semaphore

from diskcache import Cache

from codeguard.claude_provider import ClaudeJudge, PromptCacheWarmup
from codeguard.codex_provider import CodexJudge
from codeguard.config import JudgeConfig, JudgeModel, JudgeProvider
from codeguard.gemini_provider import BedrockClaude, GeminiJudge, VertexGemini
from codeguard.review import CachedJudge, Deadline, Judge

_JUDGEMENT_CACHE_DIR = Path.home() / ".cache" / "codeguard" / "judgements"


@dataclass(frozen=True)
class Judges:
    config: JudgeConfig = JudgeConfig()
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

    def cached(
        self, root: Path, model: JudgeModel, deadline: Deadline | None = None
    ) -> CachedJudge:
        return CachedJudge(self.uncached(root, model, deadline), self.store, root)

    def uncached(self, root: Path, model: JudgeModel, deadline: Deadline | None = None) -> Judge:
        processes = self.processes[model.provider]
        if model.provider is JudgeProvider.CODEX_CLI:
            return CodexJudge(root, model.required_name, processes, deadline=deadline)
        if model.provider is JudgeProvider.GEMINI:
            return GeminiJudge(
                root, model.required_name, self._vertex_gemini(), processes, deadline=deadline
            )
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

    def _vertex_gemini(self) -> VertexGemini:
        return VertexGemini(
            project=self.config.project or environ.get("GOOGLE_CLOUD_PROJECT"),
            location=self.config.location or environ.get("GOOGLE_CLOUD_LOCATION") or "global",
            api_key=environ.get("GOOGLE_API_KEY") or None,
        )
