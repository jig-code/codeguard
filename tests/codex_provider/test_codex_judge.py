import io
import json
import subprocess
import time
from threading import Semaphore
from unittest.mock import Mock

import pytest

from codeguard.codex_provider import CodexJudge, codex_judge
from codeguard.codex_provider.file_server import FileServer
from codeguard.review import (
    Deadline,
    Judgement,
    JudgeNoVerdict,
    JudgeProcessError,
    JudgeTimeout,
    Verdict,
)
from codeguard.review.file_tools import FileTools


@pytest.fixture
def codex(tmp_path):
    return CodexJudge(tmp_path, "gpt-6-luna", Semaphore(1))


def test_structured_verdict_isolated_process_and_file_dependencies(
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
        (work / "loaded.jsonl").write_text('["context.py", "missing.py", "context.py"]\n')
        return subprocess.CompletedProcess(command, 0, "", "")

    process = Mock(side_effect=run)
    monkeypatch.setattr(codex_judge.subprocess, "run", process)

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
    assert "shell_tool" in command
    assert command[command.index("view_image") - 1] == "--disable"
    assert kwargs["input"] == request.prompt
    assert "OPENAI_API_KEY" not in kwargs["env"]
    assert "CODEX_API_KEY" not in kwargs["env"]
    assert kwargs["cwd"] != codex.root
    assert captured["instructions"] == request.instructions
    assert captured["schema"]["additionalProperties"] is False
    assert judgement == Judgement(
        Verdict(reason="Follows the rule.", violations=()), ("context.py", "missing.py")
    )


@pytest.mark.parametrize("stderr", ["Authentication required", "process failed"])
def test_process_errors(codex, monkeypatch, make_judge_request, stderr):
    monkeypatch.setattr(
        codex_judge.subprocess,
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

    monkeypatch.setattr(codex_judge.subprocess, "run", run)
    with pytest.raises(JudgeNoVerdict):
        codex.judge(make_judge_request())


def test_timeout(codex, monkeypatch, make_judge_request):
    def run(*args, **kwargs):
        raise subprocess.TimeoutExpired("codex", kwargs["timeout"])

    monkeypatch.setattr(codex_judge.subprocess, "run", run)
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


def test_mcp_reads_track_files_and_reject_escape(tmp_path):
    (tmp_path / "context.py").write_text("LIMIT = 5\n")
    journal = tmp_path / "journal"
    server = FileServer(FileTools(tmp_path), journal)

    assert server.result(
        "tools/call", {"name": "read_file", "arguments": {"path": "context.py"}}
    ) == {"content": [{"type": "text", "text": "     1\tLIMIT = 5\n"}]}
    assert json.loads(journal.read_text()) == ["context.py"]
    escaped = server.result("tools/call", {"name": "read_file", "arguments": {"path": "../secret"}})
    assert "outside the working directory" in escaped["content"][0]["text"]


def test_mcp_search_tracks_dependencies(tmp_path):
    (tmp_path / "context.py").write_text("LIMIT = 5\n")
    server = FileServer(FileTools(tmp_path), tmp_path / "journal")
    server.result("tools/call", {"name": "grep", "arguments": {"pattern": "LIMIT"}})
    assert server.files.loaded_files == ["context.py"]


def test_mcp_protocol(tmp_path, monkeypatch):
    server = FileServer(FileTools(tmp_path), tmp_path / "journal")
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05"}}\n'
            '{"jsonrpc":"2.0","method":"notifications/initialized"}\n'
            '{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n'
        ),
    )
    output = io.StringIO()
    monkeypatch.setattr("sys.stdout", output)
    server.serve()
    initialized, tools = map(json.loads, output.getvalue().splitlines())
    assert initialized["result"]["protocolVersion"] == "2024-11-05"
    assert {tool["name"] for tool in tools["result"]["tools"]} == {"read_file", "grep", "glob"}


CAPACITY = json.dumps(
    {
        "type": "error",
        "message": "Selected model is at capacity. Please try a different model.",
    }
)


def test_capacity_error_retries_same_model_then_returns_verdict(
    codex, monkeypatch, make_judge_request
):
    attempts = []
    waits = []

    def run(command, **kwargs):
        attempts.append(command)
        if len(attempts) == 1:
            return subprocess.CompletedProcess(command, 1, CAPACITY, "")
        (kwargs["cwd"] / "verdict.json").write_text('{"reason":"Judged.","violations":[]}')
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(codex_judge.subprocess, "run", run)
    monkeypatch.setattr(codex_judge.time, "sleep", waits.append)

    result = codex.judge(make_judge_request())

    assert result == Judgement(Verdict(reason="Judged.", violations=()))
    assert attempts == [attempts[0], attempts[0]]
    assert waits == [1.0]


def test_capacity_retries_are_bounded(codex, monkeypatch, make_judge_request):
    process = Mock(return_value=subprocess.CompletedProcess("codex", 1, CAPACITY, ""))
    waits = []
    monkeypatch.setattr(codex_judge.subprocess, "run", process)
    monkeypatch.setattr(codex_judge.time, "sleep", waits.append)

    with pytest.raises(JudgeProcessError, match="at capacity"):
        codex.judge(make_judge_request())

    assert process.call_count == 3
    assert waits == [1.0, 2.0]


def test_authentication_failure_is_not_retried(codex, monkeypatch, make_judge_request):
    process = Mock(return_value=subprocess.CompletedProcess("codex", 1, "", "Log in with ChatGPT"))
    monkeypatch.setattr(codex_judge.subprocess, "run", process)

    with pytest.raises(JudgeProcessError, match="Log in with ChatGPT"):
        codex.judge(make_judge_request())

    process.assert_called_once()


def test_retry_backoff_must_fit_within_the_call_limit(tmp_path, monkeypatch, make_judge_request):
    judge = CodexJudge(tmp_path, "gpt-6-luna", Semaphore(1), request_limit_seconds=0.5)
    process = Mock(return_value=subprocess.CompletedProcess("codex", 1, CAPACITY, ""))
    monkeypatch.setattr(codex_judge.subprocess, "run", process)

    with pytest.raises(JudgeTimeout):
        judge.judge(make_judge_request())

    process.assert_called_once()
