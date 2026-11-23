import httpx2
from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models import Model, ModelRequestParameters
from pydantic_ai.models.wrapper import WrapperModel
from pydantic_ai.settings import ModelSettings
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    stop_before_delay,
    wait_exponential,
    wait_random,
)
from tenacity.stop import stop_base
from tenacity.wait import wait_base

from codeguard.review import Deadline

_MAX_ATTEMPTS = 5
BACKOFF = wait_exponential() + wait_random(0, 1)
_TRANSIENT_STATUSES = frozenset({408, 429, 500, 502, 503, 504})


class RetryingModel(WrapperModel):
    def __init__(
        self,
        wrapped: Model,
        deadline: Deadline | None,
        wait: wait_base = BACKOFF,
    ) -> None:
        super().__init__(wrapped)
        self.deadline = deadline
        self.wait = wait

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        retrying = AsyncRetrying(
            retry=retry_if_exception(_retryable),
            wait=self.wait,
            stop=self._stop_condition,
            reraise=True,
        )
        return await retrying(super().request, messages, model_settings, model_request_parameters)

    @property
    def _stop_condition(self) -> stop_base:
        attempts = stop_after_attempt(_MAX_ATTEMPTS)
        if self.deadline is None:
            return attempts
        return attempts | stop_before_delay(self.deadline.remaining_seconds())


def _retryable(error: BaseException) -> bool:
    if isinstance(error, ModelHTTPError):
        return error.status_code in _TRANSIENT_STATUSES
    return (
        isinstance(error, ModelAPIError)
        and _failed_in_transport(error)
        and not transport_timed_out(error)
    )


def _failed_in_transport(error: ModelAPIError) -> bool:
    return isinstance(error.__cause__, httpx2.TransportError)


def transport_timed_out(error: ModelAPIError) -> bool:
    return isinstance(error.__cause__, httpx2.TimeoutException)
