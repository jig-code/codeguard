import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from codeguard.review.deadline import Deadline
from codeguard.review.judge import JudgeProcessError, JudgeTimeout


@dataclass(frozen=True)
class ProcessBudget:
    deadline: Deadline | None = None
    expires: float | None = None
    limit_message: str = "The judge process timed out."

    def remaining_seconds(self) -> float | None:
        limits = []
        if self.deadline is not None:
            limits.append(self.deadline.remaining_seconds())
        if self.expires is not None:
            limits.append(self.expires - time.monotonic())
        remaining = min(limits) if limits else None
        if remaining is not None and remaining <= 0:
            raise self.reached()
        return remaining

    def reached(self) -> JudgeTimeout:
        if self.deadline is not None and self.deadline.remaining_seconds() <= 0:
            return self.deadline.reached()
        return JudgeTimeout(self.limit_message)


def run_judge_process(
    command: list[str],
    prompt: str,
    root: Path,
    budget: ProcessBudget,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    timeout = budget.remaining_seconds()
    try:
        return subprocess.run(
            command,
            input=prompt,
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise budget.reached() from error
    except OSError as error:
        raise JudgeProcessError(f"Could not start {command[0]}: {error}") from error


def check_judge_process(process: subprocess.CompletedProcess[str], executable: str) -> None:
    if process.returncode:
        raise JudgeProcessError(
            f"{executable} exited with {process.returncode}.\n"
            f"stdout:\n{process.stdout}\nstderr:\n{process.stderr}"
        )
