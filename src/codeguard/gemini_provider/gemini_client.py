from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from os import environ
from typing import Self

import httpx2
from google.auth.exceptions import DefaultCredentialsError
from google.genai import Client
from google.genai.types import HttpOptions
from pydantic_ai.models import (
    DEFAULT_HTTP_TIMEOUT,
    Model,
    create_async_httpx2_client,
    get_user_agent,
)
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google_cloud import GoogleCloudProvider

from codeguard.review import JudgeProcessError


@dataclass(frozen=True)
class VertexGemini:
    project: str | None
    location: str
    api_key: str | None = field(repr=False)
    client_factory: Callable[..., Client] = Client
    transport: httpx2.AsyncBaseTransport | None = None

    @classmethod
    def from_config(cls, project: str | None, location: str | None) -> Self:
        return cls(
            project=project or environ.get("GOOGLE_CLOUD_PROJECT"),
            location=location or environ.get("GOOGLE_CLOUD_LOCATION") or "global",
            api_key=environ.get("GOOGLE_API_KEY") or None,
        )

    @asynccontextmanager
    async def __call__(self, model: str) -> AsyncIterator[Model]:
        # Each judgement runs on its own event loop, so it gets its own client, closed with it.
        # GoogleCloudProvider drops an API key given with a project or location, so the client
        # that keeps all three is built here.
        # pydantic-ai maps only httpx2's transport errors, so the client sends through httpx2.
        async with create_async_httpx2_client(transport=self.transport) as http:
            with self._client(http) as client:
                yield GoogleModel(model, provider=GoogleCloudProvider(client=client))

    def _client(self, http: httpx2.AsyncClient) -> Client:
        if self.api_key and self.project is None:
            raise JudgeProcessError(
                "Gemini on Vertex AI needs a project to run with an API key: set judge.project "
                "or GOOGLE_CLOUD_PROJECT."
            )
        try:
            return self.client_factory(
                vertexai=True,
                api_key=self.api_key,
                project=self.project,
                location=self.location,
                http_options=HttpOptions(
                    headers={"User-Agent": get_user_agent()},
                    httpx_async_client=http,
                    timeout=DEFAULT_HTTP_TIMEOUT * 1000,
                ),
            )
        except DefaultCredentialsError as error:
            raise JudgeProcessError(
                f"Gemini on Vertex AI found no Google credentials: {error}"
            ) from error
