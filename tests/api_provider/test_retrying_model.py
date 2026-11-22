import asyncio
import time

import httpx2
import pytest
from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models import ModelRequestParameters
from recording_sleep import RecordingSleep
from scripted_model import ScriptedModel, http_error, transport_error

from codeguard.api_provider.retrying_model import RetryingModel
from codeguard.review import Deadline


@pytest.fixture
def prompt() -> list[ModelMessage]:
    return [ModelRequest(parts=[UserPromptPart("Judge the change.")])]


class TestRetryingModel:
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
    def test_turned_away_or_broken_request_is_sent_again(self, prompt, error):
        answer = ModelResponse(parts=[TextPart("Judged.")])
        models = ScriptedModel([error, answer])
        sleep = RecordingSleep()

        response = asyncio.run(
            RetryingModel(models.model, None, sleep).request(prompt, None, ModelRequestParameters())
        )

        assert response == answer
        assert models.answers == []
        assert 1 <= sleep.waited[0] < 2

    def test_request_is_sent_at_most_five_times(self, prompt):
        errors = [http_error(429, "Quota exceeded.") for _ in range(5)]
        unsent = ModelResponse(parts=[TextPart("Judged.")])
        models = ScriptedModel([*errors, unsent])
        sleep = RecordingSleep()

        with pytest.raises(ModelHTTPError) as raised:
            asyncio.run(
                RetryingModel(models.model, None, sleep).request(
                    prompt, None, ModelRequestParameters()
                )
            )
        assert raised.value is errors[4]
        assert models.answers == [unsent]
        assert [int(wait) for wait in sleep.waited] == [1, 2, 4, 8]

    def test_sends_again_only_while_the_backoff_fits_before_the_deadline(self, prompt):
        errors = [http_error(429, "Quota exceeded.") for _ in range(5)]
        models = ScriptedModel(list(errors))
        deadline = Deadline(minutes=1, started=time.monotonic() - 56)
        sleep = RecordingSleep()

        with pytest.raises(ModelHTTPError) as raised:
            asyncio.run(
                RetryingModel(models.model, deadline, sleep).request(
                    prompt, None, ModelRequestParameters()
                )
            )
        assert raised.value is errors[2]
        assert models.answers == errors[3:]
        assert [int(wait) for wait in sleep.waited] == [1, 2]

    def test_timed_out_request_is_not_sent_again(self, prompt):
        timeout = transport_error(httpx2.ReadTimeout("timed out"))
        models = ScriptedModel([timeout])
        sleep = RecordingSleep()

        with pytest.raises(ModelAPIError) as raised:
            asyncio.run(
                RetryingModel(models.model, None, sleep).request(
                    prompt, None, ModelRequestParameters()
                )
            )
        assert raised.value is timeout
        assert sleep.waited == []
