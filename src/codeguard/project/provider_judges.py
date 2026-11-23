from dataclasses import dataclass, field
from os import process_cpu_count
from pathlib import Path
from threading import Semaphore

from codeguard.api_provider import ApiJudge, BedrockClaude, VertexGemini
from codeguard.claude_provider import ClaudeJudge, PromptCacheWarmup
from codeguard.codex_provider import CodexJudge
from codeguard.config import GeminiSettings, JudgeConfig, JudgeModel, JudgeProvider, sent_effort
from codeguard.review import Deadline, Judge


@dataclass(frozen=True)
class ProviderJudges:
    config: JudgeConfig = JudgeConfig()
    gemini: GeminiSettings = field(default_factory=GeminiSettings)
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

    def __call__(self, root: Path, model: JudgeModel, deadline: Deadline | None = None) -> Judge:
        processes = self.processes[model.provider]
        thinking = self.config.thinking
        if model.provider is JudgeProvider.CODEX_CLI:
            return CodexJudge(
                root,
                model.required_name,
                processes,
                deadline=deadline,
                thinking=sent_effort(thinking.codex_cli),
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
                sent_effort(thinking.gemini),
                self.config.request_time_limit_seconds,
                deadline=deadline,
            )
        if model.provider is JudgeProvider.BEDROCK:
            return ApiJudge(
                root,
                model.required_name,
                BedrockClaude(),
                processes,
                model.provider,
                sent_effort(thinking.bedrock),
                self.config.request_time_limit_seconds,
                deadline=deadline,
            )
        return ClaudeJudge(
            root,
            model.name,
            processes,
            warmup=self.warmup,
            deadline=deadline,
            thinking=sent_effort(thinking.claude_cli),
        )
