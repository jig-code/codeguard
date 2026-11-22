import asyncio

import httpx2
import pytest
from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models import ModelRequestParameters
from scripted_model import ScriptedModel, http_error, transport_error
from tenacity import wait_none

from codeguard.api_provider.retrying_model import RetryingModel


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

        response = asyncio.run(
            RetryingModel(models.model, None, wait_none()).request(
                prompt, None, ModelRequestParameters()
            )
        )

        assert response == answer
        assert models.answers == []

    def test_bad_request_is_not_sent_again(self, prompt):
        error = http_error(400, "Bad request.")
        unsent = ModelResponse(parts=[TextPart("Judged.")])
        models = ScriptedModel([error, unsent])

        with pytest.raises(ModelHTTPError) as raised:
            asyncio.run(
                RetryingModel(models.model, None, wait_none()).request(
                    prompt, None, ModelRequestParameters()
                )
            )
        assert raised.value is error
        assert models.answers == [unsent]

    def test_timed_out_request_is_not_sent_again(self, prompt):
        timeout = transport_error(httpx2.ReadTimeout("timed out"))
        unsent = ModelResponse(parts=[TextPart("Judged.")])
        models = ScriptedModel([timeout, unsent])

        with pytest.raises(ModelAPIError) as raised:
            asyncio.run(
                RetryingModel(models.model, None, wait_none()).request(
                    prompt, None, ModelRequestParameters()
                )
            )
        assert raised.value is timeout
        assert models.answers == [unsent]
