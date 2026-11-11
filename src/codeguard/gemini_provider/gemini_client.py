import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass

from google.auth.exceptions import DefaultCredentialsError
from google.genai import Client
from pydantic_ai.models import Model
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google_cloud import GoogleCloudProvider

from codeguard.review import JudgeProcessError


@dataclass(frozen=True)
class VertexGemini:
    project: str | None = None
    location: str | None = None
    cloud: Callable[..., GoogleCloudProvider] = GoogleCloudProvider
    genai: Callable[..., Client] = Client

    @asynccontextmanager
    async def __call__(self, model: str) -> AsyncIterator[Model]:
        # Each judgement runs on its own event loop, so it gets its own HTTP client.
        async with GoogleModel(model, provider=self._provider()) as connected:
            yield connected

    def _provider(self) -> GoogleCloudProvider:
        project = self.project or os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = self.location or os.environ.get("GOOGLE_CLOUD_LOCATION") or "global"
        if api_key := _api_key():
            # GoogleCloudProvider drops an API key given with a project or location, so the
            # client that keeps all three is built here.
            return self.cloud(
                client=self.genai(
                    vertexai=True, api_key=api_key, project=project, location=location
                )
            )
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
