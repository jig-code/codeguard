from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

import anyio
from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse
from pydantic_ai.models import Model
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.profiles import ModelProfile

MODEL = "gemini-judge-test"


def http_error(status: int, message: str) -> ModelHTTPError:
    return ModelHTTPError(status, MODEL, body={"error": {"message": message}})


def transport_error(cause: Exception) -> ModelAPIError:
    error = ModelAPIError(MODEL, str(cause))
    error.__cause__ = cause
    return error


class Stall:
    pass


@dataclass
class ScriptedModel:
    answers: list[ModelResponse | Exception | Stall]
    requests: list[tuple[list[ModelMessage], AgentInfo]] = field(default_factory=list)
    connected: list[str] = field(default_factory=list)

    @property
    def model(self) -> FunctionModel:
        return FunctionModel(self._answer, profile=ModelProfile(supports_thinking=True))

    @asynccontextmanager
    async def __call__(self, model: str) -> AsyncIterator[Model]:
        self.connected.append(model)
        yield self.model

    async def _answer(self, messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        self.requests.append((list(messages), info))
        answer = self.answers.pop(0)
        if isinstance(answer, Stall):
            await anyio.sleep(10)
            raise AssertionError("The stalled request wasn't cut off.")
        if isinstance(answer, Exception):
            raise answer
        return answer

    def info(self, request: int = 0) -> AgentInfo:
        return self.requests[request][1]

    def sent(self, request: int) -> list[object]:
        last = self.requests[request][0][-1]
        assert isinstance(last, ModelRequest)
        return list(last.parts)
