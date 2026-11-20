from collections.abc import Iterable
from dataclasses import dataclass, field
from os import process_cpu_count
from pathlib import Path
from threading import Semaphore

from diskcache import Cache

from codeguard.api_provider import ApiJudge, BedrockClaude, VertexGemini
from codeguard.claude_provider import ClaudeJudge, PromptCacheWarmup
from codeguard.codex_provider import CodexJudge
from codeguard.config import GeminiSettings, JudgeConfig, JudgeModel, JudgeProvider
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

    def require_sign_ins(self, models: Iterable[JudgeModel]) -> None:
        if any(model.provider is JudgeProvider.GEMINI for model in models):
            self.gemini.check_sign_in()

    def cached(
        self, root: Path, model: JudgeModel, deadline: Deadline | None = None
    ) -> CachedJudge:
        return CachedJudge(self.uncached(root, model, deadline), self.store, root)

    def uncached(self, root: Path, model: JudgeModel, deadline: Deadline | None = None) -> Judge:
        processes = self.processes[model.provider]
        thinking = self.config.thinking
        if model.provider is JudgeProvider.CODEX_CLI:
            return CodexJudge(
                root, model.required_name, processes, deadline=deadline, thinking=thinking.codex_cli
            )
        if model.provider is JudgeProvider.GEMINI:
            gemini = self.gemini
            models = VertexGemini(
                gemini.project, gemini.location, gemini.api_key, gemini.credentials_file
            )
            return ApiJudge(
                root,
                model.required_name,
                models,
                processes,
                model.provider,
                thinking.gemini,
                deadline=deadline,
            )
        if model.provider is JudgeProvider.BEDROCK:
            return ApiJudge(
                root,
                model.required_name,
                BedrockClaude(),
                processes,
                model.provider,
                thinking.bedrock,
                deadline=deadline,
            )
        return ClaudeJudge(
            root,
            model.name,
            processes,
            warmup=self.warmup,
            deadline=deadline,
            thinking=thinking.claude_cli,
        )
