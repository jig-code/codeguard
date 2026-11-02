import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

import httpx2
import pytest
from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models import Model
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.usage import RequestUsage
from spans import finished_span_attributes

from codeguard.gemini_provider import GeminiJudge, gemini_judge
from codeguard.review import (
    Deadline,
    Judgement,
    JudgeNoVerdict,
    JudgeProcessError,
    JudgeTimeout,
    Verdict,
)

MODEL = "gemini-3.1-pro-preview"
VIOLATION = {
    "file": "a.py",
    "line": 1,
    "message": "Move it.",
    "confidence": 0.5,
}


def verdict(*violations: dict[str, object], input_tokens: int = 10) -> ModelResponse:
    return ModelResponse(
        parts=[TextPart(Verdict.model_validate({"violations": violations}).model_dump_json())],
        usage=_usage(input_tokens),
    )


def calls(*tools: tuple[str, dict[str, object]], input_tokens: int = 10) -> ModelResponse:
    return ModelResponse(
        parts=[ToolCallPart(name, args, tool_call_id=f"{name}-id") for name, args in tools],
        usage=_usage(input_tokens),
    )


def confidence_scale(schema: dict[str, object]) -> object:
    definitions = schema["$defs"]
    assert isinstance(definitions, dict)
    violation = definitions["Violation"]["properties"]["confidence"]
    assert violation["$ref"] == "#/$defs/Confidence"
    return definitions["Confidence"]["enum"]


def _usage(input_tokens: int) -> RequestUsage:
    return RequestUsage(
        input_tokens=input_tokens,
        output_tokens=3,
        cache_read_tokens=4,
        details={"thoughts_tokens": 5},
    )


def http_error(status: int, message: str) -> ModelHTTPError:
    return ModelHTTPError(status, MODEL, body={"error": {"message": message}})


def transport_error(cause: Exception) -> ModelAPIError:
    error = ModelAPIError(MODEL, str(cause))
    error.__cause__ = cause
    return error


@dataclass
class ScriptedGemini:
    answers: list[ModelResponse | Exception]
    requests: list[tuple[list[ModelMessage], AgentInfo]] = field(default_factory=list)
    connected: list[str] = field(default_factory=list)

    @asynccontextmanager
    async def __call__(self, model: str) -> AsyncIterator[Model]:
        self.connected.append(model)
        yield FunctionModel(self._answer)

    def _answer(self, messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        self.requests.append((list(messages), info))
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    def info(self, request: int = 0) -> AgentInfo:
        return self.requests[request][1]

    def sent(self, request: int) -> list[object]:
        last = self.requests[request][0][-1]
        assert isinstance(last, ModelRequest)
        return list(last.parts)


@dataclass
class RecordingProcesses:
    events: list[str] = field(default_factory=list)

    def __enter__(self) -> None:
        self.events.append("acquired")

    def __exit__(self, *exc_info: object) -> None:
        self.events.append("released")


@pytest.fixture(autouse=True)
def reviewed_file(tmp_path) -> None:
    (tmp_path / "a.py").write_text("print(1)\n")
    (tmp_path / "logger.py").write_text("def info(message): ...\n")


@pytest.fixture
def waits(monkeypatch) -> list[float]:
    waited: list[float] = []

    async def wait(seconds: float) -> None:
        waited.append(seconds)

    monkeypatch.setattr(gemini_judge.asyncio, "sleep", wait)
    return waited


def judge_with(tmp_path, models, **kwargs) -> GeminiJudge:
    return GeminiJudge(tmp_path, MODEL, models, RecordingProcesses(), **kwargs)


class TestGeminiJudge:
    def test_verdict_is_the_structured_output(self, tmp_path, make_judge_request):
        models = ScriptedGemini([verdict(VIOLATION)])

        judgement = judge_with(tmp_path, models).judge(make_judge_request())

        assert judgement == Judgement(Verdict.model_validate({"violations": [VIOLATION]}))

    def test_asks_for_the_verdict_as_native_structured_output(self, tmp_path, make_judge_request):
        models = ScriptedGemini([verdict()])

        judge_with(tmp_path, models).judge(make_judge_request())

        parameters = models.info().model_request_parameters
        assert parameters.output_mode == "native"
        assert parameters.output_object
        assert parameters.output_object.name == "Verdict"
        assert parameters.output_object.description == Verdict.__doc__
        assert parameters.output_tools == []

    def test_gemini_is_given_only_the_confidence_scale(self, tmp_path, make_judge_request):
        models = ScriptedGemini([verdict()])

        judge_with(tmp_path, models).judge(make_judge_request())

        output_object = models.info().model_request_parameters.output_object
        assert output_object
        assert confidence_scale(output_object.json_schema) == [1.0, 0.9, 0.7, 0.5]

    def test_bedrock_is_given_only_the_confidence_scale(self, tmp_path, make_judge_request):
        models = ScriptedGemini([calls(("final_result", {"violations": []}))])

        judge_with(tmp_path, models, provider="bedrock").judge(make_judge_request())

        [output_tool] = models.info().output_tools
        assert confidence_scale(output_tool.parameters_json_schema) == [1.0, 0.9, 0.7, 0.5]

    def test_offers_the_file_tools(self, tmp_path, make_judge_request):
        models = ScriptedGemini([verdict()])

        judge_with(tmp_path, models).judge(make_judge_request())

        assert [tool.name for tool in models.info().function_tools] == [
            "read_file",
            "grep",
            "glob",
        ]

    def test_sends_the_instructions_and_the_prompt(self, tmp_path, make_judge_request):
        models = ScriptedGemini([verdict()])
        request = make_judge_request()

        judge_with(tmp_path, models).judge(request)

        assert models.connected == [MODEL]
        assert models.info().instructions == request.instructions.strip()
        assert [part.content for part in models.sent(0) if isinstance(part, UserPromptPart)] == [
            request.prompt
        ]

    def test_thinks_at_a_low_level(self, tmp_path, make_judge_request):
        models = ScriptedGemini([verdict()])

        judge_with(tmp_path, models).judge(make_judge_request())

        settings = models.info().model_settings or {}
        assert settings.get("google_thinking_config") == {
            "thinking_level": "LOW",
            "include_thoughts": True,
        }

    def test_loaded_files_are_the_files_gemini_read_grepped_and_globbed_in_any_order(
        self, tmp_path, make_judge_request
    ):
        (tmp_path / "audit.py").write_text("from logger import info\n")
        (tmp_path / "config.toml").write_text("level = 'info'\n")
        models = ScriptedGemini(
            [
                calls(
                    ("read_file", {"path": "logger.py"}),
                    ("grep", {"pattern": "info", "glob": "**/*.py"}),
                    ("glob", {"pattern": "*.toml"}),
                ),
                verdict(),
            ]
        )

        judgement = judge_with(tmp_path, models).judge(make_judge_request())

        assert sorted(judgement.loaded_files) == ["audit.py", "config.toml", "logger.py"]

    def test_missing_file_gemini_tried_to_read_is_a_loaded_file(self, tmp_path, make_judge_request):
        models = ScriptedGemini([calls(("read_file", {"path": "orders/__init__.py"})), verdict()])

        judgement = judge_with(tmp_path, models).judge(make_judge_request())

        assert judgement.loaded_files == ("orders/__init__.py",)

    def test_file_outside_the_root_is_not_a_loaded_file(self, tmp_path, make_judge_request):
        models = ScriptedGemini([calls(("read_file", {"path": "../outside.py"})), verdict()])

        judgement = judge_with(tmp_path, models).judge(make_judge_request())

        assert judgement.loaded_files == ()

    def test_answers_file_tool_calls_before_the_verdict(self, tmp_path, make_judge_request):
        models = ScriptedGemini([calls(("read_file", {"path": "logger.py"})), verdict()])

        judge_with(tmp_path, models).judge(make_judge_request())

        assert [part.content for part in models.sent(1) if isinstance(part, ToolReturnPart)] == [
            "     1\tdef info(message): ...\n"
        ]

    def test_invalid_verdict_is_sent_back_to_correct(self, tmp_path, make_judge_request):
        invalid = ModelResponse(parts=[TextPart('{"violations": [{"file": "a.py"}]}')])
        models = ScriptedGemini([invalid, verdict()])

        judgement = judge_with(tmp_path, models).judge(make_judge_request())

        assert judgement == Judgement(Verdict(violations=()))
        assert any(isinstance(part, RetryPromptPart) for part in models.sent(1))

    def test_no_verdict_within_the_request_limit_is_a_judge_error(
        self, tmp_path, make_judge_request
    ):
        models = ScriptedGemini([calls(("glob", {"pattern": "*.py"})) for _ in range(2)])

        with pytest.raises(JudgeNoVerdict, match=f"^{MODEL} returned no verdict in 2 requests.$"):
            judge_with(tmp_path, models, max_requests=2).judge(make_judge_request())

    def test_http_error_is_a_judge_error(self, tmp_path, make_judge_request):
        unsent = verdict()
        models = ScriptedGemini([http_error(400, "Bad request."), unsent])

        with pytest.raises(JudgeProcessError, match=f"^{MODEL} failed with 400: Bad request.$"):
            judge_with(tmp_path, models).judge(make_judge_request())
        assert models.answers == [unsent]

    @pytest.mark.parametrize(
        "error",
        [
            http_error(429, "Quota exceeded."),
            http_error(503, "Unavailable."),
            transport_error(httpx2.ReadError("Connection reset by peer")),
            transport_error(httpx2.RemoteProtocolError("Server disconnected")),
        ],
        ids=["quota", "unavailable", "connection reset", "disconnected"],
    )
    def test_turned_away_or_broken_request_is_sent_again(
        self, tmp_path, make_judge_request, waits, error
    ):
        models = ScriptedGemini([error, verdict()])

        judgement = judge_with(tmp_path, models).judge(make_judge_request())

        assert judgement == Judgement(Verdict(violations=()))
        assert models.answers == []
        assert 1 <= waits[0] < 2

    def test_request_is_sent_at_most_five_times(self, tmp_path, make_judge_request, waits):
        unsent = verdict()
        models = ScriptedGemini([*(http_error(429, "Quota exceeded.") for _ in range(5)), unsent])

        with pytest.raises(JudgeProcessError, match=f"^{MODEL} failed with 429: Quota exceeded.$"):
            judge_with(tmp_path, models).judge(make_judge_request())
        assert models.answers == [unsent]
        assert [int(wait) for wait in waits] == [1, 2, 4, 8]

    def test_sends_again_only_while_the_backoff_fits_before_the_deadline(
        self, tmp_path, make_judge_request, waits
    ):
        models = ScriptedGemini([http_error(429, "Quota exceeded.") for _ in range(5)])
        deadline = Deadline(minutes=1, started=time.monotonic() - 56)

        with pytest.raises(JudgeProcessError):
            judge_with(tmp_path, models, deadline=deadline).judge(make_judge_request())
        assert [int(wait) for wait in waits] == [1, 2]

    def test_timeout_is_the_request_limit_error_without_sending_again(
        self, tmp_path, make_judge_request, waits
    ):
        models = ScriptedGemini([transport_error(httpx2.ReadTimeout("timed out"))])

        with pytest.raises(JudgeTimeout, match=f"^{MODEL} took over 120s to answer.$"):
            judge_with(tmp_path, models).judge(make_judge_request())
        assert waits == []

    def test_timeout_at_the_deadline_is_the_time_limit_error(self, tmp_path, make_judge_request):
        @asynccontextmanager
        async def slow(model: str) -> AsyncIterator[Model]:
            def answer(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
                time.sleep(0.2)
                raise transport_error(httpx2.ReadTimeout("timed out"))

            yield FunctionModel(answer)

        deadline = Deadline(minutes=1, started=time.monotonic() - 59.9)

        with pytest.raises(JudgeTimeout, match="^The review reached its 1-minute time limit.$"):
            judge_with(tmp_path, slow, deadline=deadline).judge(make_judge_request())

    def test_call_after_the_deadline_is_a_judge_error_without_calling_gemini(
        self, tmp_path, make_judge_request
    ):
        models = ScriptedGemini([verdict()])
        deadline = Deadline(minutes=1, started=time.monotonic() - 60)

        with pytest.raises(JudgeTimeout, match="^The review reached its 1-minute time limit.$"):
            judge_with(tmp_path, models, deadline=deadline).judge(make_judge_request())
        assert models.requests == []

    def test_requests_time_out_at_the_request_limit(self, tmp_path, make_judge_request):
        models = ScriptedGemini([verdict()])

        judge_with(tmp_path, models, request_limit_seconds=90).judge(make_judge_request())

        assert (models.info().model_settings or {}).get("timeout") == 90

    def test_request_times_out_at_the_deadline(self, tmp_path, make_judge_request):
        models = ScriptedGemini([verdict()])
        deadline = Deadline(minutes=1, started=time.monotonic() - 30)

        judge_with(tmp_path, models, deadline=deadline).judge(make_judge_request())

        timeout = (models.info().model_settings or {}).get("timeout")
        assert isinstance(timeout, float) and 29 < timeout <= 30

    def test_each_call_holds_a_process_slot(self, tmp_path, make_judge_request):
        processes = RecordingProcesses()

        GeminiJudge(tmp_path, MODEL, ScriptedGemini([verdict()]), processes).judge(
            make_judge_request()
        )

        assert processes.events == ["acquired", "released"]

    def test_identity_names_the_provider_and_model(self, tmp_path):
        assert judge_with(tmp_path, ScriptedGemini([])).identity == f"gemini\0{MODEL}"

    def test_call_records_its_usage_across_requests(
        self, tmp_path, make_skill, capfire, make_judge_request
    ):
        models = ScriptedGemini(
            [calls(("glob", {"pattern": "*.py"}), input_tokens=10), verdict(input_tokens=20)]
        )

        judge_with(tmp_path, models).judge(make_judge_request())

        assert finished_span_attributes(capfire, "gemini judges {rule} on {file}") == [
            {
                "rule": make_skill().name,
                "file": "a.py",
                "model": MODEL,
                "num_turns": 2,
                "input_tokens": 30,
                "output_tokens": 6,
                "cache_read_input_tokens": 8,
                "thinking_tokens": 10,
                "tool_calls": '[{"tool":"glob","pattern":"*.py"}]',
            }
        ]

    def test_call_records_the_tools_gemini_called_with_their_arguments(
        self, tmp_path, capfire, make_judge_request
    ):
        models = ScriptedGemini(
            [
                calls(
                    ("read_file", {"path": "logger.py"}),
                    ("grep", {"pattern": "def info", "glob": "**/*.py"}),
                ),
                calls(("read_file", {"path": "../outside.py", "offset": 3})),
                verdict(),
            ]
        )

        judge_with(tmp_path, models).judge(make_judge_request())

        [attributes] = finished_span_attributes(capfire, "gemini judges {rule} on {file}")
        assert attributes["tool_calls"] == (
            '[{"tool":"read_file","path":"logger.py","offset":1},'
            '{"tool":"grep","pattern":"def info","glob":"**/*.py"},'
            '{"tool":"read_file","path":"../outside.py","offset":3}]'
        )

    def test_call_without_a_verdict_records_the_tools_gemini_called(
        self, tmp_path, capfire, make_judge_request
    ):
        models = ScriptedGemini([calls(("glob", {"pattern": "*.py"})) for _ in range(2)])

        with pytest.raises(JudgeNoVerdict):
            judge_with(tmp_path, models, max_requests=2).judge(make_judge_request())

        [attributes] = finished_span_attributes(capfire, "gemini judges {rule} on {file}")
        assert attributes["tool_calls"] == (
            '[{"tool":"glob","pattern":"*.py"},{"tool":"glob","pattern":"*.py"}]'
        )
