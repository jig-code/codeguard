import json
import time
from pathlib import Path
from threading import Semaphore

import pytest
from fake_cli import FAKE_CODEX, configure_fake_cli_response
from spans import finished_span_attributes

from codeguard.codex_provider import CodexJudge
from codeguard.review import (
    Deadline,
    Judgement,
    JudgeNoVerdict,
    JudgeProcessError,
    JudgeTimeout,
    Verdict,
)

pytestmark = pytest.mark.usefixtures("fake_cli_config")

MODEL = "gpt-6-luna"


@pytest.fixture
def record(tmp_path) -> Path:
    return tmp_path / "record.json"


@pytest.fixture
def fake_codex_executable(tmp_path, record) -> str:
    configure_fake_cli_response(
        {
            "record": str(record),
            "answer": '{"reason":"Follows the rule.","violations":[]}',
            "stdout": '{"type":"turn.completed","usage":{"input_tokens":10,"output_tokens":5}}\n',
        }
    )
    return str(FAKE_CODEX)


@pytest.fixture
def processes() -> Semaphore:
    return Semaphore(1)


class TestCodexJudge:
    def test_verdict_is_the_structured_output(
        self, tmp_path, processes, fake_codex_executable, make_judge_request
    ):
        judge = CodexJudge(tmp_path, MODEL, processes, fake_codex_executable)

        judgement = judge.judge(make_judge_request())

        assert judgement == Judgement(Verdict(reason="Follows the rule.", violations=()))

    def test_sends_the_instructions_prompt_and_schema(
        self, tmp_path, processes, fake_codex_executable, record, make_judge_request
    ):
        judge = CodexJudge(tmp_path, MODEL, processes, fake_codex_executable)
        request = make_judge_request()

        judge.judge(request)

        received = json.loads(record.read_text())
        assert received["prompt"] == request.prompt
        assert received["instructions"] == request.instructions
        assert received["schema"]["additionalProperties"] is False

    def test_uses_ephemeral_read_only_native_tools(
        self, tmp_path, processes, fake_codex_executable, record, make_judge_request
    ):
        judge = CodexJudge(tmp_path, MODEL, processes, fake_codex_executable)

        judge.judge(make_judge_request())

        received = json.loads(record.read_text())
        arguments = received["arguments"]
        assert arguments[0] == "exec"
        assert "--ephemeral" in arguments
        assert "--ignore-user-config" in arguments
        assert "--ignore-rules" in arguments
        assert arguments[arguments.index("--sandbox") + 1] == "read-only"
        assert "features.skip_host_skill_discovery=true" in arguments
        assert "project_doc_max_bytes=0" in arguments
        assert 'web_search="disabled"' in arguments
        assert "shell_tool" not in arguments
        assert not any("mcp_servers" in argument for argument in arguments)
        assert arguments[arguments.index("view_image") - 1] == "--disable"
        assert arguments[arguments.index("--cd") + 1] == str(tmp_path.resolve())
        assert received["cwd"] != str(tmp_path)
        assert not Path(received["cwd"]).exists()

    def test_requires_subscription_auth_without_api_credentials(
        self, tmp_path, fake_codex_executable, record, make_judge_request, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "metered-key")
        monkeypatch.setenv("CODEX_API_KEY", "metered-key")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid")
        judge = CodexJudge(tmp_path, MODEL, Semaphore(1), fake_codex_executable)

        judge.judge(make_judge_request())

        received = json.loads(record.read_text())
        assert 'forced_login_method="chatgpt"' in received["arguments"]
        assert 'model_provider="openai"' in received["arguments"]
        assert "OPENAI_API_KEY" not in received["environment"]
        assert "CODEX_API_KEY" not in received["environment"]
        assert "OPENAI_BASE_URL" not in received["environment"]
        assert "PATH" in received["environment"]

    def test_passes_the_bound_model_and_reasoning_effort(
        self, tmp_path, processes, fake_codex_executable, record, make_judge_request
    ):
        judge = CodexJudge(tmp_path, "a-bound-model", processes, fake_codex_executable)

        judge.judge(make_judge_request())

        arguments = json.loads(record.read_text())["arguments"]
        assert arguments[arguments.index("--model") + 1] == "a-bound-model"
        assert 'model_reasoning_effort="high"' in arguments

    def test_without_a_model_runs_its_own_default(
        self, tmp_path, processes, fake_codex_executable, record, make_judge_request
    ):
        judge = CodexJudge(tmp_path, None, processes, fake_codex_executable)

        judge.judge(make_judge_request())

        assert "--model" not in json.loads(record.read_text())["arguments"]

    def test_records_usage(
        self, tmp_path, processes, fake_codex_executable, capfire, make_judge_request
    ):
        judge = CodexJudge(tmp_path, MODEL, processes, fake_codex_executable)

        judge.judge(make_judge_request())

        [attributes] = finished_span_attributes(capfire, "codex judges {rule} on {file}")
        assert attributes["usage"] == '{"input_tokens":10,"output_tokens":5}'

    def test_process_failure_is_not_retried(self, tmp_path, processes, record, make_judge_request):
        attempts = tmp_path / "attempts"
        configure_fake_cli_response(
            {
                "record": str(record),
                "calls": str(attempts),
                "stderr": "process failed",
                "exit_code": 1,
            }
        )
        executable = str(FAKE_CODEX)
        judge = CodexJudge(tmp_path, MODEL, processes, str(executable))

        with pytest.raises(JudgeProcessError, match="process failed"):
            judge.judge(make_judge_request())

        assert attempts.read_text() == "called\n"

    @pytest.mark.parametrize("answer", [None, "not json", '{"reason":"Incomplete"}'])
    def test_invalid_or_missing_verdict(
        self, tmp_path, processes, record, make_judge_request, answer
    ):
        configure_fake_cli_response({"record": str(record), "answer": answer})
        executable = str(FAKE_CODEX)
        judge = CodexJudge(tmp_path, MODEL, processes, str(executable))

        with pytest.raises(JudgeNoVerdict):
            judge.judge(make_judge_request())

    def test_expired_deadline_does_not_start_process(
        self, tmp_path, processes, fake_codex_executable, record, make_judge_request
    ):
        judge = CodexJudge(
            tmp_path,
            MODEL,
            processes,
            fake_codex_executable,
            deadline=Deadline(1, time.monotonic() - 61),
        )

        with pytest.raises(JudgeTimeout, match="time limit"):
            judge.judge(make_judge_request())

        assert not record.exists()

    def test_running_past_the_deadline_is_a_timeout(
        self, tmp_path, processes, record, make_judge_request
    ):
        configure_fake_cli_response({"record": str(record), "delay": 10})
        executable = str(FAKE_CODEX)
        judge = CodexJudge(
            tmp_path,
            MODEL,
            processes,
            str(executable),
            deadline=Deadline(1, time.monotonic() - 59.5),
        )

        with pytest.raises(JudgeTimeout, match="time limit"):
            judge.judge(make_judge_request())

    def test_missing_executable(self, tmp_path, processes, make_judge_request):
        judge = CodexJudge(tmp_path, MODEL, processes, str(tmp_path / "missing-codex"))

        with pytest.raises(JudgeProcessError, match="Could not start"):
            judge.judge(make_judge_request())
