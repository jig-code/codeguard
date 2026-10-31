import asyncio
import random
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from dataclasses import dataclass
from pathlib import Path

import httpx2
import logfire
from google.genai.types import ThinkingLevel
from pydantic_ai import Agent, NativeOutput, RunContext, ToolOutput, UsageLimits
from pydantic_ai.exceptions import (
    ModelAPIError,
    ModelHTTPError,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
)
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models import Model, ModelRequestParameters
from pydantic_ai.models.google import GoogleModelSettings
from pydantic_ai.models.wrapper import WrapperModel
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import RunUsage

from codeguard.gemini_provider.file_tools import FileTools
from codeguard.review import (
    Deadline,
    Judgement,
    JudgeNoVerdict,
    JudgeProcessError,
    JudgeRequest,
    JudgeTimeout,
    Verdict,
)

_MAX_REQUESTS = 10
_REQUEST_LIMIT_SECONDS = 120
_MAX_ATTEMPTS = 5
# Responses the request can succeed on when sent again.
_RETRIED_STATUSES = frozenset({408, 429, 500, 502, 503, 504})

# Connects to Gemini and gives the model named, for the length of one judgement.
type GeminiModels = Callable[[str], AbstractAsyncContextManager[Model]]


@dataclass(frozen=True)
class GeminiJudge:
    root: Path
    model: str
    models: GeminiModels
    processes: AbstractContextManager[object]
    deadline: Deadline | None = None
    max_requests: int = _MAX_REQUESTS
    request_limit_seconds: float = _REQUEST_LIMIT_SECONDS
    provider: str = "gemini"

    @property
    def identity(self) -> str:
        return "\0".join((self.provider, self.model))

    def judge(self, request: JudgeRequest) -> Judgement:
        with (
            self.processes,
            logfire.span(
                "gemini judges {rule} on {file}",
                rule=request.skill.name,
                file=request.file,
                model=self.model,
            ) as span,
        ):
            tools = FileTools(self.root)
            usage = RunUsage()
            try:
                verdict = asyncio.run(self._judge(request, tools, usage))
            finally:
                span.set_attributes({**_telemetry(usage), "tool_calls": tuple(tools.calls)})
            return Judgement(verdict, tuple(dict.fromkeys(tools.loaded_files)))

    async def _judge(self, request: JudgeRequest, tools: FileTools, usage: RunUsage) -> Verdict:
        agent = Agent[object, Verdict](
            deps_type=object,
            instructions=request.instructions,
            # Bedrock's Converse API has no structured output, so Claude there calls a tool.
            output_type=ToolOutput(Verdict)
            if self.provider == "bedrock"
            else NativeOutput(Verdict),
            tools=tools.tools,
            model_settings=self._settings,
        )
        try:
            async with self.models(self.model) as model:
                result = await agent.run(
                    request.prompt,
                    model=_Retrying(model, self.deadline),
                    usage=usage,
                    usage_limits=UsageLimits(request_limit=self.max_requests),
                )
        except UsageLimitExceeded as error:
            raise JudgeNoVerdict(
                f"{self.model} returned no verdict in {self.max_requests} requests."
            ) from error
        except UnexpectedModelBehavior as error:
            raise JudgeNoVerdict(f"{self.model} returned no verdict: {error.message}") from error
        except ModelHTTPError as error:
            raise JudgeProcessError(
                f"{self.model} failed with {error.status_code}: {_message(error)}"
            ) from error
        except ModelAPIError as error:
            if _timed_out(error):
                raise self._timed_out() from error
            raise JudgeProcessError(f"{self.model} failed: {error.message}") from error
        return result.output

    def _settings(self, _: RunContext[object]) -> GoogleModelSettings:
        limit = self.request_limit_seconds
        if self.deadline is not None:
            limit = min(limit, self.deadline.remaining_seconds())
            if limit <= 0:
                raise self.deadline.reached()
        return {
            "timeout": limit,
            "google_thinking_config": {
                "thinking_level": ThinkingLevel.LOW,
                "include_thoughts": True,
            },
        }

    def _timed_out(self) -> JudgeTimeout:
        if self.deadline is not None and self.deadline.remaining_seconds() <= 0:
            return self.deadline.reached()
        return JudgeTimeout(f"{self.model} took over {self.request_limit_seconds:g}s to answer.")


# Sends a request again when Gemini turned it away or the connection broke, while the backoff
# fits before the deadline. The SDK's own retries miss a connection that broke after the
# response started.
class _Retrying(WrapperModel):
    def __init__(self, wrapped: Model, deadline: Deadline | None) -> None:
        super().__init__(wrapped)
        self.deadline = deadline

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        attempt = 1
        while True:
            try:
                return await super().request(messages, model_settings, model_request_parameters)
            except ModelAPIError as error:
                # Backs off 1s doubling, plus up to 1s of jitter: about 15s over 5 attempts.
                wait = 2 ** (attempt - 1) + random.random()
                if attempt == _MAX_ATTEMPTS or not _retried(error) or not self._fits(wait):
                    raise
            await asyncio.sleep(wait)
            attempt += 1

    def _fits(self, wait: float) -> bool:
        return self.deadline is None or wait < self.deadline.remaining_seconds()


def _retried(error: ModelAPIError) -> bool:
    if isinstance(error, ModelHTTPError):
        return error.status_code in _RETRIED_STATUSES
    return _transport_error(error) and not _timed_out(error)


def _transport_error(error: ModelAPIError) -> bool:
    return isinstance(error.__cause__, httpx2.TransportError)


def _timed_out(error: ModelAPIError) -> bool:
    return isinstance(error.__cause__, httpx2.TimeoutException)


def _message(error: ModelHTTPError) -> str:
    body = error.body
    if isinstance(body, dict):
        details = body.get("error")
        if isinstance(details, dict) and isinstance(message := details.get("message"), str):
            return message
    return str(body)


def _telemetry(usage: RunUsage) -> dict[str, object]:
    return {
        "num_turns": usage.requests,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_read_input_tokens": usage.cache_read_tokens,
        "thinking_tokens": usage.details.get("thoughts_tokens", 0),
    }
