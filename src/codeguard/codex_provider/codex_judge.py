import json
import os
import subprocess
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import logfire
from pydantic import ValidationError

from codeguard.codex_provider.codex_result import CodexResult
from codeguard.codex_provider.verdict_schema import verdict_schema
from codeguard.config import CodexEffort
from codeguard.review import (
    DEFAULT_MODEL_KEY,
    Deadline,
    Judgement,
    JudgeNoVerdict,
    JudgeRequest,
    Verdict,
)
from codeguard.review.judge_process import check_judge_process, run_judge_process

_DISABLED = (
    "hooks",
    "plugins",
    "apps",
    "memories",
    "multi_agent",
    "view_image",
    "js_repl",
    "code_mode",
    "skill_search",
)


@dataclass(frozen=True)
class CodexJudge:
    root: Path
    model: str
    processes: AbstractContextManager[object]
    executable: str = "codex"
    deadline: Deadline | None = None
    # None runs at the CLI's own default reasoning effort.
    thinking: CodexEffort | None = None

    @property
    def identity(self) -> str:
        return "\0".join(
            (
                "codex-cli",
                self.model,
                f"thinking={self.thinking or DEFAULT_MODEL_KEY}",
                "native-tools-schema-v4",
            )
        )

    def judge(self, request: JudgeRequest) -> Judgement:
        with (
            self.processes,
            logfire.span(
                "codex judges {rule} on {file}",
                rule=request.judge_rule.name,
                file=request.file,
                model=self.model,
            ) as span,
            TemporaryDirectory(prefix="codeguard-codex-") as directory,
        ):
            work = Path(directory)
            schema = work / "verdict.schema.json"
            schema.write_text(json.dumps(verdict_schema()))
            instructions = work / "instructions.md"
            instructions.write_text(request.instructions)
            answer = work / "verdict.json"
            command = self._command(schema, instructions, answer)
            process = self._run(command, request.prompt, work)
            span.set_attribute("returncode", process.returncode)
            check_judge_process(process, self.executable)
            judgement = _judgement(answer)
            span.set_attribute("loaded_files", judgement.loaded_files)
            span.set_attributes(CodexResult.from_stream(process.stdout).telemetry)
            return judgement

    def _run(self, command: list[str], prompt: str, work: Path) -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        for key in ("OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL"):
            environment.pop(key, None)
        return run_judge_process(command, prompt, work, self.deadline, environment)

    def _command(self, schema: Path, instructions: Path, answer: Path) -> list[str]:
        settings: dict[str, object] = {
            "approval_policy": "never",
            "forced_login_method": "chatgpt",
            "model_provider": "openai",
            "model_instructions_file": str(instructions),
            "project_doc_max_bytes": 0,
            "web_search": "disabled",
            "features.skip_host_skill_discovery": True,
            "features.omit_skill_descriptions": True,
        }
        if self.thinking:
            settings["model_reasoning_effort"] = self.thinking
        return [
            self.executable,
            "exec",
            "--ignore-user-config",
            "--ignore-rules",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "--skip-git-repo-check",
            "--cd",
            str(self.root.resolve()),
            "--model",
            self.model,
            "--json",
            "--output-schema",
            str(schema),
            "--output-last-message",
            str(answer),
            *(argument for name in _DISABLED for argument in ("--disable", name)),
            *(
                argument
                for key, value in settings.items()
                for argument in ("-c", f"{key}={json.dumps(value)}")
            ),
            "-",
        ]


def _judgement(answer: Path) -> Judgement:
    try:
        return Judgement(Verdict.model_validate_json(answer.read_text()))
    except (OSError, ValueError, ValidationError) as error:
        raise JudgeNoVerdict(f"Codex returned no valid verdict: {error}") from error
