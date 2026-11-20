import asyncio
import random
from collections.abc import Callable, Sequence
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from dataclasses import dataclass
from pathlib import Path

import httpx2
import logfire
from pydantic import BaseModel, JsonValue, ValidationError
from pydantic_ai import (
    Agent,
    RunContext,
    ToolOutput,
    UsageLimits,
    capture_run_messages,
)
from pydantic_ai.exceptions import (
    ModelAPIError,
    ModelHTTPError,
    ModelRequestTimeout,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
)
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models import Model, ModelRequestParameters
from pydantic_ai.models.wrapper import WrapperModel
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import RunUsage
from pydantic_ai.workspaces import LocalWorkspaceBackend

from codeguard.api_provider.file_system import (
    PATH_WITH_RIPGREP,
    file_system_tools,
    file_tool_calls,
    loaded_files,
)
from codeguard.config import ApiEffort
from codeguard.review import (
    DEFAULT_THINKING_KEY,
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
_GEMINI_THINKING_TOKENS = "thoughts_tokens"
# Responses the request can succeed on when sent again.
_RETRIED_STATUSES = frozenset({408, 429, 500, 502, 503, 504})

# Connects to the provider and gives the model named, for the length of one judgement.
type ApiModels = Callable[[str], AbstractAsyncContextManager[Model]]


@dataclass(frozen=True)
class ApiJudge:
    root: Path
    model: str
    models: ApiModels
    processes: AbstractContextManager[object]
    provider: str
    thinking: ApiEffort | None
    deadline: Deadline | None = None
    max_requests: int = _MAX_REQUESTS
    request_limit_seconds: float = _REQUEST_LIMIT_SECONDS

    @property
    def identity(self) -> str:
        return "\0".join(
            (self.provider, self.model, f"thinking={self.thinking or DEFAULT_THINKING_KEY}")
        )

    def judge(self, request: JudgeRequest) -> Judgement:
        with (
            self.processes,
            logfire.span(
                "{provider} judges {rule} on {file}",
                provider=self.provider,
                rule=request.judge_rule.name,
                file=request.file,
                model=self.model,
            ) as span,
        ):
            usage = RunUsage()
            with capture_run_messages() as messages:
                try:
                    verdict = asyncio.run(
                        self._run(request.instructions, request.prompt, Verdict, usage)
                    )
                finally:
                    span.set_attributes({**_telemetry(usage), "tool_calls": _tool_calls(messages)})
            return Judgement(verdict, loaded_files(messages))

    async def _run[Output: BaseModel](
        self,
        instructions: str,
        prompt: str,
        output: type[Output],
        usage: RunUsage,
    ) -> Output:
        agent = Agent[object, Output](
            deps_type=object,
            instructions=instructions,
            output_type=ToolOutput(output),
            capabilities=[file_system_tools(self.root)],
            model_settings=self._settings,
        )
        try:
            async with self.models(self.model) as model:
                result = await agent.run(
                    prompt,
                    model=_Retrying(model, self.deadline),
                    workspace=LocalWorkspaceBackend(self.root, env={"PATH": PATH_WITH_RIPGREP}),
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
        except ValidationError as error:
            # The SDK validated a request it was given, which no other call shares.
            raise JudgeProcessError(
                f"{self.model} couldn't send the request: {error.title} rejected "
                f"{error.error_count()} field(s)."
            ) from error
        return result.output

    def _settings(self, _: RunContext[object]) -> ModelSettings:
        limit = self.request_limit_seconds
        if self.deadline is not None:
            limit = min(limit, self.deadline.remaining_seconds())
            if limit <= 0:
                raise self.deadline.reached()
        settings: ModelSettings = {"request_timeout": limit}
        if self.thinking is not None:
            settings["thinking"] = self.thinking
        return settings

    def _timed_out(self) -> JudgeTimeout:
        if self.deadline is not None and self.deadline.remaining_seconds() <= 0:
            return self.deadline.reached()
        return JudgeTimeout(f"{self.model} took over {self.request_limit_seconds:g}s to answer.")


# Sends a request again when the provider turned it away or the connection broke, while the backoff
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
    return isinstance(error, ModelRequestTimeout) or isinstance(
        error.__cause__, httpx2.TimeoutException
    )


def _message(error: ModelHTTPError) -> str:
    body = error.body
    if isinstance(body, dict):
        details = body.get("error")
        if isinstance(details, dict) and isinstance(message := details.get("message"), str):
            return message
    return str(body)


def _tool_calls(messages: Sequence[ModelMessage]) -> tuple[dict[str, JsonValue], ...]:
    """The file tools the model called, with the arguments it sent, in the order it called
    them. The tools run concurrently, so the order they ran in says nothing."""
    return tuple(
        {"tool": call.tool_name, **call.args_as_dict()} for call in file_tool_calls(messages)
    )


def _telemetry(usage: RunUsage) -> dict[str, object]:
    return {
        "num_turns": usage.requests,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_read_input_tokens": usage.cache_read_tokens,
        "thinking_tokens": usage.output_reasoning_tokens
        or usage.details.get(_GEMINI_THINKING_TOKENS, 0),
    }
