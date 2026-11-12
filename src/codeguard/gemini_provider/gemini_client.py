import os
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass

import httpx2
from google.auth.credentials import Credentials
from google.auth.exceptions import DefaultCredentialsError
from google.genai import Client
from google.genai.types import HttpOptions
from pydantic_ai.models import Model, create_async_httpx2_client
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google_cloud import GoogleCloudProvider

from codeguard.review import JudgeProcessError


@dataclass(frozen=True)
class VertexGemini:
    project: str | None = None
    location: str | None = None
    credentials: Credentials | None = None
    transport: httpx2.AsyncBaseTransport | None = None

    @asynccontextmanager
    async def __call__(self, model: str) -> AsyncIterator[Model]:
        # Each judgement runs on its own event loop, so it gets its own HTTP client.
        async with create_async_httpx2_client(transport=self.transport) as http:
            with self._client(http) as client:
                provider = GoogleCloudProvider(client=client)
                async with GoogleModel(model, provider=provider) as connected:
                    yield connected

    # GoogleCloudProvider can't send an API key together with a project, so codeguard builds
    # the client for every sign-in.
    @contextmanager
    def _client(self, http: httpx2.AsyncClient) -> Iterator[Client]:
        project = self.project or os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = self.location or os.environ.get("GOOGLE_CLOUD_LOCATION") or "global"
        api_key = _api_key()
        if api_key is not None and project is None:
            raise JudgeProcessError(
                "Gemini on Vertex AI needs a project to use with the API key: set judge.project "
                "in .codeguard/config.yaml or GOOGLE_CLOUD_PROJECT"
            )
        try:
            client = Client(
                vertexai=True,
                api_key=api_key,
                credentials=None if api_key else self.credentials,
                project=project,
                location=location,
                http_options=HttpOptions(httpx_async_client=http),
            )
        except DefaultCredentialsError as error:
            raise JudgeProcessError(
                f"Gemini on Vertex AI found no Google credentials: {error}"
            ) from error
        with client:
            yield client


def _api_key() -> str | None:
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return None
    return os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or None
