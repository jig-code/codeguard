import asyncio
import time

import httpx2
import pytest
from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models import ModelRequestParameters
from scripted_gemini import ScriptedGemini, http_error, transport_error

from codeguard.api_provider.retrying_model import RetryingModel
from codeguard.review import Deadline

PROMPT = [ModelRequest(parts=[UserPromptPart("Judge the change.")])]


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
    def test_turned_away_or_broken_request_is_sent_again(self, waits, error):
        answer = ModelResponse(parts=[TextPart("Judged.")])
        models = ScriptedGemini([error, answer])

        response = asyncio.run(
            RetryingModel(models.model, None).request(PROMPT, None, ModelRequestParameters())
        )

        assert response == answer
        assert models.answers == []
        assert 1 <= waits[0] < 2

    def test_request_is_sent_at_most_five_times(self, waits):
        unsent = ModelResponse(parts=[TextPart("Judged.")])
        models = ScriptedGemini([*(http_error(429, "Quota exceeded.") for _ in range(5)), unsent])

        with pytest.raises(ModelHTTPError):
            asyncio.run(
                RetryingModel(models.model, None).request(PROMPT, None, ModelRequestParameters())
            )
        assert models.answers == [unsent]
        assert [int(wait) for wait in waits] == [1, 2, 4, 8]

    def test_sends_again_only_while_the_backoff_fits_before_the_deadline(self, waits):
        models = ScriptedGemini([http_error(429, "Quota exceeded.") for _ in range(5)])
        deadline = Deadline(minutes=1, started=time.monotonic() - 56)

        with pytest.raises(ModelHTTPError):
            asyncio.run(
                RetryingModel(models.model, deadline).request(
                    PROMPT, None, ModelRequestParameters()
                )
            )
        assert [int(wait) for wait in waits] == [1, 2]

    def test_timed_out_request_is_not_sent_again(self, waits):
        timeout = transport_error(httpx2.ReadTimeout("timed out"))
        models = ScriptedGemini([timeout])

        with pytest.raises(ModelAPIError) as raised:
            asyncio.run(
                RetryingModel(models.model, None).request(PROMPT, None, ModelRequestParameters())
            )
        assert raised.value is timeout
        assert waits == []
