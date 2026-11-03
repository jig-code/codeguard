import json
import os
import subprocess
import sys
import time
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import logfire
from pydantic import ValidationError

from codeguard.codex_provider.verdict_schema import verdict_schema
from codeguard.review import (
    Deadline,
    Judgement,
    JudgeNoVerdict,
    JudgeProcessError,
    JudgeRequest,
    JudgeTimeout,
    Verdict,
)

_DISABLED = (
    "hooks",
    "plugins",
    "apps",
    "memories",
    "multi_agent",
    "shell_tool",
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
    request_limit_seconds: float = 120

    @property
    def identity(self) -> str:
        return "\0".join(("codex-cli", self.model, "reasoning=high", "mcp-files-schema-v2"))

    def judge(self, request: JudgeRequest) -> Judgement:
        with (
            self.processes,
            logfire.span(
                "codex judges {rule} on {file}",
                rule=request.skill.name,
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
            journal = work / "loaded.jsonl"
            answer = work / "verdict.json"
            command = self._command(work, schema, instructions, journal, answer)
            process, attempts = self._run(command, request.prompt, work)
            span.set_attribute("attempts", attempts)
            span.set_attribute("returncode", process.returncode)
            if process.returncode:
                raise JudgeProcessError(
                    f"{self.executable} exited with {process.returncode}: {process.stderr}\n"
                    f"{process.stdout}"
                )
            judgement = _judgement(answer, journal)
            span.set_attribute("loaded_files", judgement.loaded_files)
            span.set_attributes(_usage(process.stdout))
            return judgement

    def _run(
        self, command: list[str], prompt: str, work: Path
    ) -> tuple[subprocess.CompletedProcess[str], int]:
        expires = time.monotonic() + self.request_limit_seconds
        environment = dict(os.environ)
        for key in ("OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL"):
            environment.pop(key, None)
        for attempt in range(1, 4):
            timeout = expires - time.monotonic()
            if self.deadline is not None:
                timeout = min(timeout, self.deadline.remaining_seconds())
            if timeout <= 0:
                raise self._timed_out()
            (work / "verdict.json").unlink(missing_ok=True)
            try:
                process = subprocess.run(
                    command,
                    input=prompt,
                    cwd=work,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired as error:
                raise self._timed_out() from error
            except OSError as error:
                raise JudgeProcessError(f"Could not start {self.executable}: {error}") from error
            if process.returncode == 0 or attempt == 3 or not _at_capacity(process.stdout):
                return process, attempt
            wait = float(attempt)
            remaining = expires - time.monotonic()
            if self.deadline is not None:
                remaining = min(remaining, self.deadline.remaining_seconds())
            if wait >= remaining:
                raise self._timed_out()
            time.sleep(wait)
        raise AssertionError("unreachable")

    def _timed_out(self) -> JudgeTimeout:
        if self.deadline is not None and self.deadline.remaining_seconds() <= 0:
            return self.deadline.reached()
        return JudgeTimeout(f"{self.model} took over {self.request_limit_seconds:g}s to answer.")

    def _command(
        self, work: Path, schema: Path, instructions: Path, journal: Path, answer: Path
    ) -> list[str]:
        settings = {
            "approval_policy": "never",
            "forced_login_method": "chatgpt",
            "model_provider": "openai",
            "model_reasoning_effort": "high",
            "model_instructions_file": str(instructions),
            "project_doc_max_bytes": 0,
            "web_search": "disabled",
            "features.skip_host_skill_discovery": True,
            "features.omit_skill_descriptions": True,
            "mcp_servers.codeguard.command": sys.executable,
            "mcp_servers.codeguard.args": [
                "-m",
                "codeguard.codex_provider.file_server",
                str(self.root.resolve()),
                str(journal),
            ],
            "mcp_servers.codeguard.required": True,
        }
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
            str(work),
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


def _judgement(answer: Path, journal: Path) -> Judgement:
    try:
        verdict = Verdict.model_validate_json(answer.read_text())
        loaded: list[str] = []
        if journal.exists():
            for line in journal.read_text().splitlines():
                files = json.loads(line)
                if not isinstance(files, list) or not all(isinstance(file, str) for file in files):
                    raise ValueError("Invalid file journal")
                loaded.extend(files)
        return Judgement(verdict, tuple(dict.fromkeys(loaded)))
    except (OSError, ValueError, ValidationError) as error:
        raise JudgeNoVerdict(f"Codex returned no valid verdict: {error}") from error


def _usage(stream: str) -> dict[str, object]:
    for line in reversed(stream.splitlines()):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("type") == "turn.completed":
            return {"usage": event.get("usage", {})}
    return {}


def _at_capacity(stream: str) -> bool:
    for line in stream.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if (
            isinstance(event, dict)
            and event.get("type") == "error"
            and event.get("message")
            == "Selected model is at capacity. Please try a different model."
        ):
            return True
    return False
