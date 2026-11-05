import subprocess
from pathlib import Path

from codeguard.review.deadline import Deadline
from codeguard.review.judge import JudgeProcessError, JudgeTimeout


def run_judge_process(
    command: list[str],
    prompt: str,
    root: Path,
    deadline: Deadline | None,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    timeout = deadline.remaining_seconds() if deadline is not None else None
    if deadline is not None and timeout is not None and timeout <= 0:
        raise deadline.reached()
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
        if deadline is not None:
            raise deadline.reached() from error
        raise JudgeTimeout("The judge process timed out.") from error
    except OSError as error:
        raise JudgeProcessError(f"Could not start {command[0]}: {error}") from error


def check_judge_process(process: subprocess.CompletedProcess[str], executable: str) -> None:
    if process.returncode:
        raise JudgeProcessError(
            f"{executable} exited with {process.returncode}.\n"
            f"stdout:\n{process.stdout}\nstderr:\n{process.stderr}"
        )
