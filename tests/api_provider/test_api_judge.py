import subprocess
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

import anyio
import httpx2
import pytest
from google.genai.types import GenerateContentConfig
from pydantic import SecretStr, ValidationError
from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models import Model
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.profiles import ModelProfile
from pydantic_ai.usage import RequestUsage
from spans import finished_span_attributes

from codeguard.api_provider import ApiJudge, VertexGemini, api_judge
from codeguard.config import ApiEffort
from codeguard.review import (
    Deadline,
    Judgement,
    JudgeNoVerdict,
    JudgeProcessError,
    JudgeTimeout,
    Verdict,
)

MODEL = "gemini-judge-test"
VIOLATION = {
    "file": "a.py",
    "lines": {"start": 1, "end": 1},
    "message": "Move it.",
}


def verdict(*violations: dict[str, object], input_tokens: int = 10) -> ModelResponse:
    answer = Verdict.model_validate({"reason": "Judged.", "violations": violations})
    return calls(("final_result", answer.model_dump(mode="json")), input_tokens=input_tokens)


def calls(*tools: tuple[str, dict[str, object]], input_tokens: int = 10) -> ModelResponse:
    return ModelResponse(
        parts=[ToolCallPart(name, args, tool_call_id=f"{name}-id") for name, args in tools],
        usage=_usage(input_tokens),
    )


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
        yield FunctionModel(self._answer, profile=ModelProfile(supports_thinking=True))

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


@dataclass
class VertexVerdicts:
    verdict: Verdict
    sent: list[httpx2.Request] = field(default_factory=list)

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.sent.append(request)
        answer = {"name": "final_result", "args": self.verdict.model_dump(mode="json")}
        return httpx2.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {"role": "model", "parts": [{"functionCall": answer}]},
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5},
            },
        )


@pytest.fixture(autouse=True)
def reviewed_file(tmp_path) -> None:
    (tmp_path / "a.py").write_text("print(1)\n")
    (tmp_path / "logger.py").write_text("def info(message): ...\n")


@pytest.fixture
def waits(monkeypatch) -> list[float]:
    waited: list[float] = []

    async def wait(seconds: float) -> None:
        waited.append(seconds)

    monkeypatch.setattr(api_judge.asyncio, "sleep", wait)
    return waited


def judge_with(
    tmp_path, models, provider: str = "gemini", thinking: ApiEffort | None = "medium", **kwargs
) -> ApiJudge:
    return ApiJudge(tmp_path, MODEL, models, RecordingProcesses(), provider, thinking, **kwargs)


class TestApiJudge:
    def test_verdict_is_the_structured_output(self, tmp_path, make_judge_request):
        models = ScriptedGemini([verdict(VIOLATION)])

        judgement = judge_with(tmp_path, models).judge(make_judge_request())

        assert judgement == Judgement(
            Verdict.model_validate({"reason": "Judged.", "violations": [VIOLATION]})
        )

    def test_offers_the_file_tools(self, tmp_path, make_judge_request):
        models = ScriptedGemini([verdict()])

        judge_with(tmp_path, models).judge(make_judge_request())

        assert [tool.name for tool in models.info().function_tools] == [
            "read_file",
            "search_files",
            "list_files",
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

    def test_thinks_at_the_level_it_is_given(self, tmp_path, make_judge_request):
        models = ScriptedGemini([verdict()])

        judge_with(tmp_path, models, thinking="xhigh").judge(make_judge_request())

        assert models.info().model_request_parameters.thinking == "xhigh"

    def test_without_a_level_sends_none(self, tmp_path, make_judge_request):
        models = ScriptedGemini([verdict()])

        judge_with(tmp_path, models, thinking=None).judge(make_judge_request())

        assert models.info().model_request_parameters.thinking is None

    def test_loaded_files_are_the_files_gemini_read_searched_and_listed_in_call_order(
        self, tmp_path, make_judge_request
    ):
        (tmp_path / "audit.py").write_text("from logger import info\n")
        (tmp_path / "config.toml").write_text("level = 'info'\n")
        models = ScriptedGemini(
            [
                calls(
                    ("read_file", {"path": "logger.py"}),
                    ("search_files", {"pattern": "info", "include_glob": "*.py"}),
                    ("list_files", {"glob": "*.toml"}),
                ),
                verdict(),
            ]
        )

        judgement = judge_with(tmp_path, models).judge(make_judge_request())

        assert judgement.loaded_files == ("logger.py", "audit.py", "config.toml")

    def test_listing_loads_its_first_200_files_and_not_its_truncation_notice(
        self, tmp_path, make_judge_request
    ):
        (tmp_path / "orders").mkdir()
        for number in range(201):
            (tmp_path / "orders" / f"order_{number:03}.py").write_text("")
        models = ScriptedGemini([calls(("list_files", {"path": "orders"})), verdict()])

        judgement = judge_with(tmp_path, models).judge(make_judge_request())

        assert judgement.loaded_files == tuple(f"orders/order_{n:03}.py" for n in range(200))

    def test_matched_line_holding_a_form_feed_names_only_its_own_file(
        self, tmp_path, make_judge_request
    ):
        (tmp_path / "audit.py").write_text("info = 'a\x0corders.py:1:'\n")
        models = ScriptedGemini([calls(("search_files", {"pattern": "info ="})), verdict()])

        judgement = judge_with(tmp_path, models).judge(make_judge_request())

        assert judgement.loaded_files == ("audit.py",)

    def test_files_git_ignores_are_not_listed(self, tmp_path, make_judge_request):
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        (tmp_path / ".gitignore").write_text("node_modules/\n")
        (tmp_path / "node_modules" / "pkg").mkdir(parents=True)
        (tmp_path / "node_modules" / "pkg" / "log.py").write_text("def info(message): ...\n")
        models = ScriptedGemini([calls(("list_files", {"glob": "*.py"})), verdict()])

        judgement = judge_with(tmp_path, models).judge(make_judge_request())

        assert judgement.loaded_files == ("a.py", "logger.py")

    def test_missing_file_gemini_tried_to_read_is_a_loaded_file(self, tmp_path, make_judge_request):
        models = ScriptedGemini([calls(("read_file", {"path": "orders/__init__.py"})), verdict()])

        judgement = judge_with(tmp_path, models).judge(make_judge_request())

        assert judgement.loaded_files == ("orders/__init__.py",)

    def test_file_outside_the_root_is_not_a_loaded_file(self, tmp_path, make_judge_request):
        models = ScriptedGemini([calls(("read_file", {"path": "../outside.py"})), verdict()])

        judgement = judge_with(tmp_path, models).judge(make_judge_request())

        assert judgement.loaded_files == ()

    def test_invalid_verdict_is_sent_back_to_correct(self, tmp_path, make_judge_request):
        invalid = calls(("final_result", {"violations": [{"file": "a.py"}]}))
        models = ScriptedGemini([invalid, verdict()])

        judgement = judge_with(tmp_path, models).judge(make_judge_request())

        assert judgement == Judgement(Verdict(reason="Judged.", violations=()))
        (feedback,) = models.sent(1)
        assert isinstance(feedback, ToolReturnPart)
        assert feedback.outcome == "retried"
        assert feedback.content == [
            {
                "type": "missing",
                "loc": ["reason"],
                "msg": "Field required",
                "input": {"violations": [{"file": "a.py"}]},
            },
            {
                "type": "missing",
                "loc": ["violations", 0, "lines"],
                "msg": "Field required",
                "input": {"file": "a.py"},
            },
            {
                "type": "missing",
                "loc": ["violations", 0, "message"],
                "msg": "Field required",
                "input": {"file": "a.py"},
            },
        ]

    def test_no_verdict_within_the_request_limit_is_a_judge_error(
        self, tmp_path, make_judge_request
    ):
        models = ScriptedGemini([calls(("list_files", {"glob": "*.py"})) for _ in range(2)])

        with pytest.raises(JudgeNoVerdict, match=f"^{MODEL} returned no verdict in 2 requests.$"):
            judge_with(tmp_path, models, max_requests=2).judge(make_judge_request())

    def test_http_error_is_a_judge_error(self, tmp_path, make_judge_request):
        unsent = verdict()
        models = ScriptedGemini([http_error(400, "Bad request."), unsent])

        with pytest.raises(JudgeProcessError, match=f"^{MODEL} failed with 400: Bad request.$"):
            judge_with(tmp_path, models).judge(make_judge_request())
        assert models.answers == [unsent]

    def test_request_the_sdk_rejects_is_a_judge_error(self, tmp_path, make_judge_request):
        with pytest.raises(ValidationError) as rejected:
            GenerateContentConfig.model_validate({"unknown": 1})
        models = ScriptedGemini([rejected.value])

        with pytest.raises(
            JudgeProcessError,
            match=f"^{MODEL} couldn't send the request: GenerateContentConfig rejected 1 field",
        ):
            judge_with(tmp_path, models).judge(make_judge_request())

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

        assert judgement == Judgement(Verdict(reason="Judged.", violations=()))
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

    def test_request_running_past_the_request_limit_is_the_request_limit_error(
        self, tmp_path, make_judge_request
    ):
        @asynccontextmanager
        async def slow(model: str) -> AsyncIterator[Model]:
            async def answer(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
                await anyio.sleep(10)
                return verdict()

            yield FunctionModel(answer)

        with pytest.raises(JudgeTimeout, match=f"^{MODEL} took over 0.1s to answer.$"):
            judge_with(tmp_path, slow, request_limit_seconds=0.1).judge(make_judge_request())

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

        assert (models.info().model_settings or {}).get("request_timeout") == 90

    def test_request_times_out_at_the_deadline(self, tmp_path, make_judge_request):
        models = ScriptedGemini([verdict()])
        deadline = Deadline(minutes=1, started=time.monotonic() - 30)

        judge_with(tmp_path, models, deadline=deadline).judge(make_judge_request())

        timeout = (models.info().model_settings or {}).get("request_timeout")
        assert isinstance(timeout, float) and 29 < timeout <= 30

    def test_each_call_holds_a_process_slot(self, tmp_path, make_judge_request):
        processes = RecordingProcesses()

        ApiJudge(tmp_path, MODEL, ScriptedGemini([verdict()]), processes, "gemini", "medium").judge(
            make_judge_request()
        )

        assert processes.events == ["acquired", "released"]

    def test_identity_names_the_provider_model_and_thinking_level(self, tmp_path):
        assert judge_with(tmp_path, ScriptedGemini([]), thinking="low").identity == (
            f"gemini\0{MODEL}\0thinking=low"
        )

    def test_identity_without_a_level_names_the_model_default(self, tmp_path):
        assert judge_with(tmp_path, ScriptedGemini([]), thinking=None).identity == (
            f"gemini\0{MODEL}\0thinking=default"
        )

    def test_call_records_its_usage_across_requests(
        self, tmp_path, make_judge_rule, capfire, make_judge_request
    ):
        models = ScriptedGemini(
            [calls(("list_files", {"glob": "*.py"}), input_tokens=10), verdict(input_tokens=20)]
        )

        judge_with(tmp_path, models).judge(make_judge_request())

        assert finished_span_attributes(capfire, "{provider} judges {rule} on {file}") == [
            {
                "provider": "gemini",
                "rule": make_judge_rule().name,
                "file": "a.py",
                "model": MODEL,
                "num_turns": 2,
                "input_tokens": 30,
                "output_tokens": 6,
                "cache_read_input_tokens": 8,
                "thinking_tokens": 10,
                "tool_calls": '[{"tool":"list_files","glob":"*.py"}]',
            }
        ]

    def test_call_records_the_tools_gemini_called_with_their_arguments(
        self, tmp_path, capfire, make_judge_request
    ):
        models = ScriptedGemini(
            [
                calls(
                    ("read_file", {"path": "logger.py"}),
                    ("search_files", {"pattern": "def info", "include_glob": "*.py"}),
                ),
                calls(("read_file", {"path": "../outside.py", "offset": 3})),
                verdict(),
            ]
        )

        judge_with(tmp_path, models).judge(make_judge_request())

        [attributes] = finished_span_attributes(capfire, "{provider} judges {rule} on {file}")
        assert attributes["tool_calls"] == (
            '[{"tool":"read_file","path":"logger.py"},'
            '{"tool":"search_files","pattern":"def info","include_glob":"*.py"},'
            '{"tool":"read_file","path":"../outside.py","offset":3}]'
        )

    def test_call_does_not_record_the_verdict_tool(self, tmp_path, capfire, make_judge_request):
        models = ScriptedGemini([calls(("list_files", {"glob": "*.py"})), verdict()])

        judge_with(tmp_path, models).judge(make_judge_request())

        [attributes] = finished_span_attributes(capfire, "{provider} judges {rule} on {file}")
        assert attributes["tool_calls"] == '[{"tool":"list_files","glob":"*.py"}]'

    def test_call_without_a_verdict_records_the_tools_gemini_called(
        self, tmp_path, capfire, make_judge_request
    ):
        models = ScriptedGemini([calls(("list_files", {"glob": "*.py"})) for _ in range(2)])

        with pytest.raises(JudgeNoVerdict):
            judge_with(tmp_path, models, max_requests=2).judge(make_judge_request())

        [attributes] = finished_span_attributes(capfire, "{provider} judges {rule} on {file}")
        assert attributes["tool_calls"] == (
            '[{"tool":"list_files","glob":"*.py"},{"tool":"list_files","glob":"*.py"}]'
        )


class TestApiJudgeOnVertex:
    def test_api_key_judges_in_the_project_and_location(
        self, tmp_path, make_judge_request, make_verdict
    ):
        verdict = make_verdict()
        vertex = VertexVerdicts(verdict)
        models = VertexGemini(
            "my-project",
            "europe-west4",
            api_key=SecretStr("proxy-injected"),
            transport=httpx2.MockTransport(vertex),
        )

        judgement = judge_with(tmp_path, models).judge(make_judge_request())

        assert judgement == Judgement(verdict)
        [request] = vertex.sent
        assert "/projects/my-project/locations/europe-west4/" in request.url.path
        assert f"/models/{MODEL}:" in request.url.path
        assert request.headers["x-goog-api-key"] == "proxy-injected"
