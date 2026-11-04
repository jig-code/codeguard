import json
import subprocess
import time
from threading import Semaphore
from unittest.mock import Mock

import pytest

from codeguard.codex_provider import CodexJudge
from codeguard.review import (
    Deadline,
    Judgement,
    JudgeNoVerdict,
    JudgeProcessError,
    JudgeTimeout,
    Verdict,
    judge_process,
)


@pytest.fixture
def codex(tmp_path):
    return CodexJudge(tmp_path, "gpt-6-luna", Semaphore(1))


def test_structured_verdict_with_native_tools_and_subscription_auth(
    codex, monkeypatch, make_judge_request
):
    monkeypatch.setenv("OPENAI_API_KEY", "metered-key")
    monkeypatch.setenv("CODEX_API_KEY", "metered-key")
    request = make_judge_request()

    captured = {}

    def run(command, **kwargs):
        work = kwargs["cwd"]
        captured["instructions"] = (work / "instructions.md").read_text()
        captured["schema"] = json.loads((work / "verdict.schema.json").read_text())
        (work / "verdict.json").write_text('{"reason":"Follows the rule.","violations":[]}')
        return subprocess.CompletedProcess(command, 0, "", "")

    process = Mock(side_effect=run)
    monkeypatch.setattr(judge_process.subprocess, "run", process)

    judgement = codex.judge(request)

    command = process.call_args.args[0]
    kwargs = process.call_args.kwargs
    assert command[:2] == ["codex", "exec"]
    assert "--ephemeral" in command
    assert "--ignore-user-config" in command
    assert command[command.index("--sandbox") + 1] == "read-only"
    assert 'forced_login_method="chatgpt"' in command
    assert "features.skip_host_skill_discovery=true" in command
    assert 'model_reasoning_effort="high"' in command
    assert "shell_tool" not in command
    assert not any("mcp_servers" in argument for argument in command)
    assert command[command.index("--cd") + 1] == str(codex.root.resolve())
    assert command[command.index("view_image") - 1] == "--disable"
    assert kwargs["input"] == request.prompt
    assert "OPENAI_API_KEY" not in kwargs["env"]
    assert "CODEX_API_KEY" not in kwargs["env"]
    assert kwargs["cwd"] != codex.root
    assert captured["instructions"] == request.instructions
    assert captured["schema"]["additionalProperties"] is False
    assert judgement == Judgement(Verdict(reason="Follows the rule.", violations=()))


@pytest.mark.parametrize("stderr", ["Authentication required", "process failed"])
def test_process_errors(codex, monkeypatch, make_judge_request, stderr):
    monkeypatch.setattr(
        judge_process.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 1, "", stderr),
    )
    with pytest.raises(JudgeProcessError, match=stderr):
        codex.judge(make_judge_request())


@pytest.mark.parametrize("answer", [None, "not json", '{"reason":"Incomplete"}'])
def test_invalid_or_missing_verdict(codex, monkeypatch, make_judge_request, answer):
    def run(command, **kwargs):
        if answer is not None:
            (kwargs["cwd"] / "verdict.json").write_text(answer)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(judge_process.subprocess, "run", run)
    with pytest.raises(JudgeNoVerdict):
        codex.judge(make_judge_request())


def test_timeout(codex, monkeypatch, make_judge_request):
    def run(*args, **kwargs):
        raise subprocess.TimeoutExpired("codex", kwargs["timeout"])

    monkeypatch.setattr(judge_process.subprocess, "run", run)
    with pytest.raises(JudgeTimeout):
        codex.judge(make_judge_request())


def test_expired_deadline_does_not_start_process(tmp_path, make_judge_request):
    judge = CodexJudge(
        tmp_path,
        "gpt-6-luna",
        Semaphore(1),
        executable="must-not-run",
        deadline=Deadline(1, time.monotonic() - 61),
    )
    with pytest.raises(JudgeTimeout, match="time limit"):
        judge.judge(make_judge_request())


def test_missing_executable(tmp_path, make_judge_request):
    judge = CodexJudge(tmp_path, "gpt-6-luna", Semaphore(1), executable="missing-codex-exe")
    with pytest.raises(JudgeProcessError, match="Could not start"):
        judge.judge(make_judge_request())


def test_capacity_error_is_not_retried(codex, monkeypatch, make_judge_request):
    process = Mock(return_value=subprocess.CompletedProcess("codex", 1, "", "at capacity"))
    monkeypatch.setattr(judge_process.subprocess, "run", process)

    with pytest.raises(JudgeProcessError, match="at capacity"):
        codex.judge(make_judge_request())

    process.assert_called_once()
