import os
import re
import subprocess
from pathlib import Path

import yaml

ACTION = Path(__file__).resolve().parent.parent / "action.yml"
ALLOW_JUDGE_ERRORS_LABEL = "codeguard-allow-judge-errors"
EXPRESSION = re.compile(r"\$\{\{\s*(.*?)\s*\}\}")
FAKE_UV = (
    "#!/bin/sh\n"
    'case " $* " in\n'
    '  *" codeguard config "*) echo 5 ;;\n'
    '  *) printf "%s\\n" "$@" > "$UV_ARGS" ;;\n'
    "esac\n"
)


class TestReviewStep:
    def test_allow_judge_errors_label_passes_judge_errors_as_warnings(self, tmp_path):
        arguments = run_review_step(tmp_path, labels=["bug", ALLOW_JUDGE_ERRORS_LABEL])

        assert arguments == ["review", "--base", "origin/main", "--judge-errors-as-warnings"]

    def test_other_labels_pass_no_judge_errors_flag(self, tmp_path):
        arguments = run_review_step(tmp_path, labels=["bug"])

        assert arguments == ["review", "--base", "origin/main"]


def run_review_step(tmp_path: Path, labels: list[str]) -> list[str]:
    """Run the action's review step as GitHub would for a PR with these labels.

    Return the arguments it passes to codeguard.
    """
    steps = yaml.safe_load(ACTION.read_text())["runs"]["steps"]
    step = next(step for step in steps if step.get("id") == "review")
    values = github_values(labels)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    uv = bin_dir / "uv"
    uv.write_text(FAKE_UV)
    uv.chmod(0o755)
    uv_args = tmp_path / "uv-args"
    subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", substitute(step["run"], values)],
        check=True,
        env={
            **os.environ,
            **{name: substitute(value, values) for name, value in step["env"].items()},
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "UV_ARGS": str(uv_args),
        },
    )
    arguments = uv_args.read_text().splitlines()
    return arguments[arguments.index("codeguard") + 1 :]


def github_values(labels: list[str]) -> dict[str, str]:
    """What GitHub evaluates each of the review step's expressions to, with default inputs."""
    return {
        "github.action_path": "/action",
        "inputs.base": "origin/main",
        "inputs.dry-run == 'true' && '--dry-run' || ''": "",
        "inputs.logfire-token": "",
        f"contains(github.event.pull_request.labels.*.name, '{ALLOW_JUDGE_ERRORS_LABEL}')": str(
            ALLOW_JUDGE_ERRORS_LABEL in labels
        ).lower(),
    }


def substitute(text: str, values: dict[str, str]) -> str:
    return EXPRESSION.sub(lambda match: values[match.group(1)], text)
