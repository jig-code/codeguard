import asyncio
import math
from collections.abc import Awaitable, Callable, Sequence
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from dataclasses import dataclass
from pathlib import Path

import logfire
from pydantic import BaseModel, JsonValue, ValidationError
from pydantic_ai import (
    Agent,
    RunContext,
    UsageLimits,
    capture_run_messages,
)
from pydantic_ai.exceptions import (
    FallbackExceptionGroup,
    ModelAPIError,
    ModelHTTPError,
    ModelRequestTimeout,
    RunTimedOut,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
)
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models import Model
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import RunUsage
from pydantic_ai.workspaces import LocalWorkspaceBackend

from codeguard.api_provider.file_system import (
    PATH_WITH_RIPGREP,
    file_system_tools,
    file_tool_calls,
    loaded_files,
)
from codeguard.api_provider.retrying_model import RetryingModel, transport_timed_out
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
# Judge requests answer in well under a minute. One still unanswered then has stalled at the
# provider, and the same request sent again answers in seconds.
_MAX_ATTEMPT_SECONDS = 60
_GEMINI_THINKING_TOKENS = "thoughts_tokens"

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
    request_time_limit_seconds: float
    deadline: Deadline | None = None
    max_requests: int = _MAX_REQUESTS
    max_attempt_seconds: float = _MAX_ATTEMPT_SECONDS
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep

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
            output_type=output,
            capabilities=[file_system_tools(self.root)],
            model_settings=self._settings,
        )
        try:
            async with self.models(self.model) as model:
                result = await agent.run(
                    prompt,
                    model=FallbackModel(
                        *(
                            RetryingModel(model, self.deadline, self.sleep)
                            for _ in range(self._attempts_per_request)
                        ),
                        fallback_on=(ModelRequestTimeout,),
                    ),
                    timeout=None if self.deadline is None else self.deadline.remaining_seconds(),
                    workspace=LocalWorkspaceBackend(self.root, env={"PATH": PATH_WITH_RIPGREP}),
                    usage=usage,
                    usage_limits=UsageLimits(request_limit=self.max_requests),
                )
        except (FallbackExceptionGroup, RunTimedOut) as error:
            raise self._timeout_error() from error
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
            if transport_timed_out(error):
                raise self._timeout_error() from error
            raise JudgeProcessError(f"{self.model} failed: {error.message}") from error
        except ValidationError as error:
            # The SDK validated a request it was given, which no other call shares.
            raise JudgeProcessError(
                f"{self.model} couldn't send the request: {error.title} rejected "
                f"{error.error_count()} field(s)."
            ) from error
        return result.output

    @property
    def _attempts_per_request(self) -> int:
        return math.ceil(self.request_time_limit_seconds / self.max_attempt_seconds)

    @property
    def _attempt_time_limit_seconds(self) -> float:
        return self.request_time_limit_seconds / self._attempts_per_request

    def _settings(self, _: RunContext[object]) -> ModelSettings:
        settings: ModelSettings = {"request_timeout": self._attempt_time_limit_seconds}
        if self.thinking is not None:
            settings["thinking"] = self.thinking
        return settings

    def _timeout_error(self) -> JudgeTimeout:
        if self.deadline is not None and self.deadline.remaining_seconds() <= 0:
            return self.deadline.reached()
        return JudgeTimeout(
            f"{self.model} took over {self.request_time_limit_seconds:g}s to answer."
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
