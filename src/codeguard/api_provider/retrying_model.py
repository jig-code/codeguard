import asyncio
import random

import httpx2
from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models import Model, ModelRequestParameters
from pydantic_ai.models.wrapper import WrapperModel
from pydantic_ai.settings import ModelSettings

from codeguard.review import Deadline

_MAX_ATTEMPTS = 5
# Responses the request can succeed on when sent again.
_RETRIED_STATUSES = frozenset({408, 429, 500, 502, 503, 504})


# Sends a request again when the provider turned it away or the connection broke, while the backoff
# fits before the deadline. The SDK's own retries miss a connection that broke after the
# response started.
class RetryingModel(WrapperModel):
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
                backoff_seconds = 2 ** (attempt - 1) + random.random()
                if (
                    attempt == _MAX_ATTEMPTS
                    or not _retried(error)
                    or not self._fits(backoff_seconds)
                ):
                    raise
            await asyncio.sleep(backoff_seconds)
            attempt += 1

    def _fits(self, backoff_seconds: float) -> bool:
        return self.deadline is None or backoff_seconds < self.deadline.remaining_seconds()


def _retried(error: ModelAPIError) -> bool:
    if isinstance(error, ModelHTTPError):
        return error.status_code in _RETRIED_STATUSES
    return _transport_error(error) and not transport_timed_out(error)


def _transport_error(error: ModelAPIError) -> bool:
    return isinstance(error.__cause__, httpx2.TransportError)


def transport_timed_out(error: ModelAPIError) -> bool:
    return isinstance(error.__cause__, httpx2.TimeoutException)
