import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass

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
    project: str | None = None
    location: str | None = None
    cloud: Callable[..., GoogleCloudProvider] = GoogleCloudProvider
    transport: httpx2.AsyncBaseTransport | None = None

    @asynccontextmanager
    async def __call__(self, model: str) -> AsyncIterator[Model]:
        # Each judgement runs on its own event loop, so it gets its own HTTP client.
        async with self._provider() as provider, GoogleModel(model, provider=provider) as connected:
            yield connected

    @asynccontextmanager
    async def _provider(self) -> AsyncIterator[GoogleCloudProvider]:
        project = self.project or os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = self.location or os.environ.get("GOOGLE_CLOUD_LOCATION") or "global"
        api_key = _api_key()
        if api_key is None:
            yield self._signed_in_with_credentials(project, location)
            return
        if project is None:
            raise JudgeProcessError(
                "Gemini on Vertex AI needs a project to use with the API key: set judge.project "
                "in .codeguard/config.yaml or GOOGLE_CLOUD_PROJECT"
            )
        # Without a project, Vertex AI serves an API key from us-central1, which doesn't serve
        # every model, and GoogleCloudProvider drops an API key given with a project, so the
        # client that keeps both is built here.
        async with create_async_httpx2_client(transport=self.transport) as http:
            with Client(
                vertexai=True,
                api_key=api_key,
                project=project,
                location=location,
                http_options=HttpOptions(
                    headers={"User-Agent": get_user_agent()},
                    httpx_async_client=http,
                    timeout=DEFAULT_HTTP_TIMEOUT * 1000,
                ),
            ) as client:
                yield self.cloud(client=client)

    def _signed_in_with_credentials(
        self, project: str | None, location: str
    ) -> GoogleCloudProvider:
        try:
            return self.cloud(project=project, location=location)
        except DefaultCredentialsError as error:
            raise JudgeProcessError(
                f"Gemini on Vertex AI found no Google credentials: {error}"
            ) from error


def _api_key() -> str | None:
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return None
    return os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or None
