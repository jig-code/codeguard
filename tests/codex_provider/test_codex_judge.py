import json
import time
from pathlib import Path
from threading import Semaphore

import pytest
from codex_output import fake_codex_script
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

MODEL = "gpt-6-luna"


@pytest.fixture
def record(tmp_path) -> Path:
    return tmp_path / "record.json"


@pytest.fixture
def fake_codex_executable(tmp_path, record) -> str:
    executable = tmp_path / "codex"
    executable.write_text(
        fake_codex_script(record, '{"reason":"Follows the rule.","violations":[]}')
    )
    executable.chmod(0o755)
    return str(executable)


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

    def test_records_usage(
        self, tmp_path, processes, fake_codex_executable, capfire, make_judge_request
    ):
        judge = CodexJudge(tmp_path, MODEL, processes, fake_codex_executable)

        judge.judge(make_judge_request())

        [attributes] = finished_span_attributes(capfire, "codex judges {rule} on {file}")
        assert attributes["usage"] == '{"input_tokens":10,"output_tokens":5}'

    @pytest.mark.parametrize(
        "message", ["Authentication required", "process failed", "at capacity"]
    )
    def test_process_failure_is_not_retried(
        self, tmp_path, processes, record, make_judge_request, message
    ):
        attempts = tmp_path / "attempts"
        executable = tmp_path / "codex"
        executable.write_text(
            fake_codex_script(
                record,
                None,
                f"with Path({str(attempts)!r}).open('a') as calls: calls.write('called\\n')\n"
                f"sys.stderr.write({message!r})\nsys.exit(1)",
            )
        )
        executable.chmod(0o755)
        judge = CodexJudge(tmp_path, MODEL, processes, str(executable))

        with pytest.raises(JudgeProcessError, match=message):
            judge.judge(make_judge_request())

        assert attempts.read_text() == "called\n"

    @pytest.mark.parametrize("answer", [None, "not json", '{"reason":"Incomplete"}'])
    def test_invalid_or_missing_verdict(
        self, tmp_path, processes, record, make_judge_request, answer
    ):
        executable = tmp_path / "codex"
        executable.write_text(fake_codex_script(record, answer))
        executable.chmod(0o755)
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
        executable = tmp_path / "codex"
        executable.write_text(fake_codex_script(record, None, "import time\ntime.sleep(10)"))
        executable.chmod(0o755)
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
