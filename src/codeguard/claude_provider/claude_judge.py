import json
import subprocess
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from pathlib import Path

import logfire
from logfire import LogfireSpan
from pydantic import BaseModel

from codeguard.claude_provider.claude_result import ClaudeResult
from codeguard.claude_provider.prompt_cache_warmup import PromptCacheWarmup
from codeguard.review import (
    Deadline,
    Judgement,
    JudgeNoVerdict,
    JudgeRequest,
    Verdict,
    output_schema,
)
from codeguard.review.judge_process import check_judge_process, run_judge_process

_EXECUTABLE = "claude"
_READ_ONLY_TOOLS = "Read,Grep,Glob"


@dataclass(frozen=True)
class ClaudeJudge:
    root: Path
    # None runs the CLI with no --model, so its own default judges.
    model: str | None
    processes: AbstractContextManager[object]
    executable: str = _EXECUTABLE
    warmup: PromptCacheWarmup = field(default_factory=PromptCacheWarmup)
    deadline: Deadline | None = None

    @property
    def identity(self) -> str:
        return "\0".join((_EXECUTABLE, self.model or ""))

    def judge(self, request: JudgeRequest) -> Judgement:
        with logfire.span(
            "claude judges {rule} on {file}",
            rule=request.skill.name,
            file=request.file,
            model=self.model,
        ) as span:
            result = self._result(
                span, request.instructions, request.prompt, Verdict, _READ_ONLY_TOOLS
            )
            span.set_attributes(result.telemetry)
            return Judgement(Verdict.model_validate(result.structured_output), result.loaded_files)

    def _result(
        self,
        span: LogfireSpan,
        instructions: str,
        prompt: str,
        output: type[BaseModel],
        tools: str,
    ) -> ClaudeResult:
        schema = json.dumps(output_schema(output))
        with self.warmup.after_first_call((self.model, instructions)), self.processes:
            process = self._run(instructions, prompt, schema, tools)
        span.set_attribute("returncode", process.returncode)
        check_judge_process(process, self.executable)
        result = ClaudeResult.from_stream(process.stdout, self.root)
        if result.structured_output is None:
            raise JudgeNoVerdict(f"{self.executable} returned no verdict:\n{process.stdout}")
        return result

    def _run(
        self, instructions: str, prompt: str, schema: str, tools: str
    ) -> subprocess.CompletedProcess[str]:
        return run_judge_process(
            [
                self.executable,
                "--safe-mode",
                "-p",
                *(("--model", self.model) if self.model else ()),
                "--output-format",
                "stream-json",
                "--verbose",
                "--json-schema",
                schema,
                "--tools",
                tools,
                "--permission-prompts",
                "none",
                "--system-prompt",
                instructions,
                "--no-session-persistence",
            ],
            prompt,
            self.root,
            self.deadline,
        )
