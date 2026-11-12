from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from os import environ
from typing import Self

from google.auth.exceptions import DefaultCredentialsError
from google.genai import Client
from pydantic_ai.models import Model
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google_cloud import GoogleCloudProvider

from codeguard.review import JudgeProcessError


@dataclass(frozen=True)
class VertexGemini:
    project: str | None
    location: str
    api_key: str | None
    genai: Callable[..., Client] = Client

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
        with self._client() as client:
            async with (
                client.aio,
                GoogleModel(model, provider=GoogleCloudProvider(client=client)) as connected,
            ):
                yield connected

    def _client(self) -> Client:
        try:
            return self.genai(
                vertexai=True, api_key=self.api_key, project=self.project, location=self.location
            )
        except DefaultCredentialsError as error:
            raise JudgeProcessError(
                f"Gemini on Vertex AI found no Google credentials: {error}"
            ) from error
