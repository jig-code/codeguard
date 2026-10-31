import json
import time
from collections.abc import Hashable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from threading import Semaphore

import pytest
from claude_output import MODEL_USAGE, claude_result, fake_claude_script, tool_result, tool_use
from spans import finished_span_attributes

from codeguard.claude_provider import ClaudeJudge, PromptCacheWarmup
from codeguard.review import (
    Deadline,
    Judgement,
    JudgeNoVerdict,
    JudgeProcessError,
    JudgeTimeout,
    Verdict,
)

MODEL = "claude-sonnet-5-5"


@pytest.fixture
def arguments(tmp_path) -> Path:
    return tmp_path / "arguments"


@pytest.fixture
def fake_claude_executable(tmp_path, arguments) -> str:
    script = fake_claude_script(
        [
            {
                "file": "a.py",
                "line": 1,
                "message": "Move it.",
                "confidence": 0.5,
            }
        ],
        before=f'echo "$@" > {arguments}\n',
    )
    executable = tmp_path / "claude"
    executable.write_text(script)
    executable.chmod(0o755)
    return str(executable)


@pytest.fixture(autouse=True)
def reviewed_file(tmp_path) -> None:
    (tmp_path / "a.py").write_text("print(1)\n")


@pytest.fixture
def prompt(tmp_path) -> Path:
    return tmp_path / "prompt"


@pytest.fixture
def prompt_recording_claude_executable(tmp_path, prompt) -> str:
    executable = tmp_path / "claude"
    executable.write_text(fake_claude_script([], before=f"cat > {prompt}\n"))
    executable.chmod(0o755)
    return str(executable)


@pytest.fixture
def processes() -> Semaphore:
    return Semaphore(1)


@pytest.fixture
def failing_claude_executable(tmp_path) -> str:
    executable = tmp_path / "claude"
    executable.write_text(
        "#!/bin/sh\ncat > /dev/null\necho 'rate limited'\necho 'try later' >&2\nexit 1\n"
    )
    executable.chmod(0o755)
    return str(executable)


@pytest.fixture
def hanging_claude_executable(tmp_path) -> str:
    executable = tmp_path / "claude"
    executable.write_text("#!/bin/sh\nsleep 10\n")
    executable.chmod(0o755)
    return str(executable)


def claude_printing(tmp_path: Path, stream: str) -> str:
    executable = tmp_path / "claude"
    executable.write_text(f"#!/bin/sh\ncat > /dev/null\ncat <<'EOF'\n{stream}\nEOF\n")
    executable.chmod(0o755)
    return str(executable)


def deadline_in(seconds: float) -> Deadline:
    return Deadline(minutes=1, started=time.monotonic() - 60 + seconds)


@dataclass
class RecordingProcesses:
    events: list[str] = field(default_factory=list)

    def __enter__(self) -> None:
        self.events.append("acquired")

    def __exit__(self, *exc_info: object) -> None:
        self.events.append("released")


@dataclass
class RecordingWarmup(PromptCacheWarmup):
    prefixes: list[Hashable] = field(default_factory=list)

    @contextmanager
    def after_first_call(self, prefix: Hashable) -> Iterator[None]:
        self.prefixes.append(prefix)
        with super().after_first_call(prefix):
            yield


class TestClaudeJudge:
    def test_call_records_its_usage(
        self, tmp_path, processes, fake_claude_executable, capfire, make_judge_request
    ):
        judge = ClaudeJudge(tmp_path, MODEL, processes, fake_claude_executable)
        request = make_judge_request()

        judge.judge(request)

        assert finished_span_attributes(capfire, "claude judges {rule} on {file}") == [
            {
                "rule": request.skill.name,
                "file": "a.py",
                "model": MODEL,
                "returncode": 0,
                "is_error": False,
                "subtype": "success",
                "num_turns": 3,
                "duration_ms": 2036,
                "duration_api_ms": 1901,
                "cost_usd": 0.0022,
                "input_tokens": MODEL_USAGE["inputTokens"],
                "output_tokens": MODEL_USAGE["outputTokens"],
                "cache_read_input_tokens": MODEL_USAGE["cacheReadInputTokens"],
                "cache_creation_input_tokens": MODEL_USAGE["cacheCreationInputTokens"],
                "thinking_tokens": MODEL_USAGE["thinkingTokens"],
                "model_usage": json.dumps(
                    {
                        MODEL: {
                            "input_tokens": MODEL_USAGE["inputTokens"],
                            "output_tokens": MODEL_USAGE["outputTokens"],
                            "cache_read_input_tokens": MODEL_USAGE["cacheReadInputTokens"],
                            "cache_creation_input_tokens": MODEL_USAGE["cacheCreationInputTokens"],
                            "thinking_tokens": MODEL_USAGE["thinkingTokens"],
                            "cost_usd": MODEL_USAGE["costUSD"],
                        }
                    },
                    separators=(",", ":"),
                ),
                "tool_calls": "[]",
                "five_hour_utilization": 0.16,
                "seven_day_utilization": 0.11,
            }
        ]

    def test_call_records_the_tools_claude_called_with_their_arguments(
        self, tmp_path, processes, capfire, make_judge_request
    ):
        judge = judge_answering(
            tmp_path,
            processes,
            tool_use("Read", file_path=str(tmp_path / "orders/pricing.py"), offset=10),
            tool_use("Grep", "toolu_grep", pattern="DISCOUNT", glob="**/*.py"),
            tool_result("toolu_grep", mode="files_with_matches", filenames=["orders/receipt.py"]),
            tool_use("StructuredOutput", violations=[]),
        )

        judge.judge(make_judge_request())

        [attributes] = finished_span_attributes(capfire, "claude judges {rule} on {file}")
        assert attributes["tool_calls"] == json.dumps(
            [
                {
                    "tool": "Read",
                    "file_path": str(tmp_path / "orders/pricing.py"),
                    "offset": 10,
                },
                {"tool": "Grep", "pattern": "DISCOUNT", "glob": "**/*.py"},
            ],
            separators=(",", ":"),
        )

    def test_failed_call_is_a_process_error_with_claude_output(
        self, tmp_path, processes, failing_claude_executable, make_judge_request
    ):
        judge = ClaudeJudge(tmp_path, MODEL, processes, failing_claude_executable)

        with pytest.raises(JudgeProcessError) as error:
            judge.judge(make_judge_request())

        assert str(error.value) == (
            f"{failing_claude_executable} exited with 1.\n"
            "stdout:\nrate limited\n\nstderr:\ntry later\n"
        )

    def test_call_after_the_deadline_is_a_timeout_without_running_claude(
        self, tmp_path, processes, fake_claude_executable, arguments, make_judge_request
    ):
        judge = ClaudeJudge(
            tmp_path, MODEL, processes, fake_claude_executable, deadline=deadline_in(0)
        )

        with pytest.raises(JudgeTimeout, match="^The review reached its 1-minute time limit.$"):
            judge.judge(make_judge_request())
        assert not arguments.exists()

    def test_call_running_past_the_deadline_is_a_timeout(
        self, tmp_path, processes, hanging_claude_executable, make_judge_request
    ):
        judge = ClaudeJudge(
            tmp_path, MODEL, processes, hanging_claude_executable, deadline=deadline_in(0.5)
        )

        with pytest.raises(JudgeTimeout, match="^The review reached its 1-minute time limit.$"):
            judge.judge(make_judge_request())

    def test_result_without_structured_output_is_no_verdict(
        self, tmp_path, processes, make_judge_request
    ):
        result = {
            key: value for key, value in claude_result([]).items() if key != "structured_output"
        }
        executable = claude_printing(tmp_path, json.dumps(result))
        judge = ClaudeJudge(tmp_path, MODEL, processes, executable)

        with pytest.raises(JudgeNoVerdict, match="returned no verdict"):
            judge.judge(make_judge_request())

    def test_output_without_a_result_is_no_verdict(self, tmp_path, processes, make_judge_request):
        executable = claude_printing(tmp_path, json.dumps({"type": "system"}))
        judge = ClaudeJudge(tmp_path, MODEL, processes, executable)

        with pytest.raises(JudgeNoVerdict, match="^claude printed no result"):
            judge.judge(make_judge_request())

    def test_each_call_holds_a_process_slot(
        self, tmp_path, fake_claude_executable, make_judge_request
    ):
        processes = RecordingProcesses()
        judge = ClaudeJudge(tmp_path, MODEL, processes, fake_claude_executable)

        judge.judge(make_judge_request())

        assert processes.events == ["acquired", "released"]

    def test_verdict_comes_from_claude_structured_output(
        self, tmp_path, processes, fake_claude_executable, make_judge_request, make_violation
    ):
        judge = ClaudeJudge(tmp_path, MODEL, processes, fake_claude_executable)

        judgement = judge.judge(make_judge_request())

        assert judgement == Judgement(
            Verdict(violations=(make_violation(message="Move it.", confidence=0.5),))
        )

    def test_loaded_files_are_the_files_claude_read(self, tmp_path, processes, make_judge_request):
        judge = judge_answering(
            tmp_path,
            processes,
            tool_use("Read", file_path=str(tmp_path / "orders/pricing.py")),
            tool_use("Read", file_path="/etc/hostname"),
            tool_use("StructuredOutput", violations=[]),
        )

        judgement = judge.judge(make_judge_request())

        assert judgement.loaded_files == ("orders/pricing.py", "/etc/hostname")

    def test_loaded_files_include_the_files_grep_and_glob_found(
        self, tmp_path, processes, make_judge_request
    ):
        judge = judge_answering(
            tmp_path,
            processes,
            tool_use("Grep", "toolu_grep", pattern="DISCOUNT"),
            tool_result("toolu_grep", mode="files_with_matches", filenames=["orders/pricing.py"]),
            tool_use("Glob", "toolu_glob", pattern="orders/*.py"),
            tool_result("toolu_glob", filenames=["orders/pricing.py", "orders/receipt.py"]),
        )

        judgement = judge.judge(make_judge_request())

        assert judgement.loaded_files == ("orders/pricing.py", "orders/receipt.py")

    def test_loaded_files_include_the_files_in_grep_content_and_counts(
        self, tmp_path, processes, make_judge_request
    ):
        (tmp_path / "orders").mkdir()
        (tmp_path / "orders" / "pricing.py").write_text("DISCOUNT = 5\n")
        (tmp_path / "orders" / "order-service.py").write_text("total = 1 - DISCOUNT\n")
        (tmp_path / "orders" / "receipt.py").write_text("print(DISCOUNT)\n")
        judge = judge_answering(
            tmp_path,
            processes,
            tool_use("Grep", "toolu_content", pattern="DISCOUNT", output_mode="content"),
            tool_result(
                "toolu_content",
                mode="content",
                filenames=[],
                content="orders/pricing.py:1:DISCOUNT = 5\n"
                "orders/order-service.py-1-total = 1 - DISCOUNT\n--",
            ),
            tool_use("Grep", "toolu_count", pattern="DISCOUNT", output_mode="count"),
            tool_result("toolu_count", mode="count", filenames=[], content="orders/receipt.py:1"),
        )

        judgement = judge.judge(make_judge_request())

        assert judgement.loaded_files == (
            "orders/pricing.py",
            "orders/order-service.py",
            "orders/receipt.py",
        )

    def test_loaded_files_include_a_single_file_grep_searched(
        self, tmp_path, processes, make_judge_request
    ):
        (tmp_path / "ledger").mkdir()
        (tmp_path / "ledger" / "__init__.py").write_text("from ledger.entry import Entry\n")
        judge = judge_answering(
            tmp_path,
            processes,
            tool_use("Grep", "toolu_grep", pattern="Entry", path="ledger/__init__.py"),
            tool_result(
                "toolu_grep",
                mode="content",
                filenames=[],
                content="1:from ledger.entry import Entry",
            ),
        )

        judgement = judge.judge(make_judge_request())

        assert judgement.loaded_files == ("ledger/__init__.py",)

    def test_failed_search_loads_no_files(self, tmp_path, processes, make_judge_request):
        judge = judge_answering(
            tmp_path,
            processes,
            tool_use("Grep", "toolu_grep", pattern="DISCOUNT", path="orders"),
            {
                "type": "user",
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "toolu_grep",
                            "content": "<tool_use_error>No such path</tool_use_error>",
                            "is_error": True,
                        }
                    ]
                },
                "tool_use_result": "Error: Path does not exist: orders",
            },
        )

        judgement = judge.judge(make_judge_request())

        assert judgement.loaded_files == ()

    def test_claude_runs_the_given_model(
        self, tmp_path, processes, fake_claude_executable, arguments, make_judge_request
    ):
        judge = ClaudeJudge(
            tmp_path,
            model="claude-opus-5-5",
            processes=processes,
            executable=fake_claude_executable,
        )

        judge.judge(make_judge_request())

        assert "--model claude-opus-5-5" in arguments.read_text()

    def test_claude_is_given_only_the_confidence_scale(
        self, tmp_path, processes, arguments, make_judge_request
    ):
        executable = tmp_path / "claude"
        executable.write_text(
            fake_claude_script([], before=f"printf '%s\\0' \"$@\" > {arguments}\n")
        )
        executable.chmod(0o755)
        judge = ClaudeJudge(tmp_path, MODEL, processes, str(executable))

        judge.judge(make_judge_request())

        argv = arguments.read_text().split("\0")
        schema = json.loads(argv[argv.index("--json-schema") + 1])
        confidence = schema["$defs"]["Violation"]["properties"]["confidence"]
        assert confidence["$ref"] == "#/$defs/Confidence"
        assert schema["$defs"]["Confidence"] == {
            "enum": [1.0, 0.9, 0.7, 0.5],
            "title": "Confidence",
            "type": "number",
        }

    def test_claude_has_only_read_only_tools(
        self, tmp_path, processes, fake_claude_executable, arguments, make_judge_request
    ):
        judge = ClaudeJudge(tmp_path, MODEL, processes, fake_claude_executable)

        judge.judge(make_judge_request())

        assert "--tools Read,Grep,Glob" in arguments.read_text()

    def test_claude_gets_the_skill_as_the_prompt(
        self, tmp_path, processes, prompt_recording_claude_executable, prompt, make_judge_request
    ):
        judge = ClaudeJudge(tmp_path, MODEL, processes, prompt_recording_claude_executable)
        request = make_judge_request()

        judge.judge(request)

        assert prompt.read_text() == request.prompt

    def test_claude_gets_the_file_in_the_system_prompt(
        self, tmp_path, processes, fake_claude_executable, arguments, make_judge_request
    ):
        judge = ClaudeJudge(tmp_path, MODEL, processes, fake_claude_executable)
        request = make_judge_request()

        judge.judge(request)

        assert f"--system-prompt {request.instructions}" in arguments.read_text()

    def test_calls_wait_for_the_first_call_with_their_prefix(
        self, tmp_path, processes, fake_claude_executable, make_judge_request
    ):
        warmup = RecordingWarmup()
        judge = ClaudeJudge(tmp_path, MODEL, processes, fake_claude_executable, warmup)
        request = make_judge_request()

        judge.judge(request)

        assert warmup.prefixes == [(MODEL, request.instructions)]

    def test_identity_changes_with_the_model(self, tmp_path, processes):
        sonnet = ClaudeJudge(tmp_path, model="claude-sonnet-5-5", processes=processes)
        opus = ClaudeJudge(tmp_path, model="claude-opus-5-5", processes=processes)

        assert sonnet.identity != opus.identity


def judge_answering(tmp_path, processes, *messages: dict) -> ClaudeJudge:
    executable = tmp_path / "claude"
    executable.write_text(fake_claude_script([], messages=messages))
    executable.chmod(0o755)
    return ClaudeJudge(tmp_path, MODEL, processes, str(executable))
