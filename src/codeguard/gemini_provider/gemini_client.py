import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from google.auth.exceptions import DefaultCredentialsError
from pydantic_ai.models import Model
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google_cloud import GoogleCloudProvider

from codeguard.review import JudgeProcessError


@dataclass(frozen=True)
class VertexGemini:
    project: str | None = None
    location: str | None = None

    @asynccontextmanager
    async def __call__(self, model: str) -> AsyncIterator[Model]:
        # Each judgement runs on its own event loop, so it gets its own HTTP client.
        async with GoogleModel(model, provider=self._provider()) as connected:
            yield connected

    def _provider(self) -> GoogleCloudProvider:
        project = self.project or os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = self.location or os.environ.get("GOOGLE_CLOUD_LOCATION")
        if project is None and location is None and _api_key():
            # An API key identifies the project.
            return GoogleCloudProvider()
        try:
            return GoogleCloudProvider(project=project, location=location or "global")
        except DefaultCredentialsError as error:
            raise JudgeProcessError(
                f"Gemini on Vertex AI found no Google credentials: {error}"
            ) from error


def _api_key() -> bool:
    return bool(os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")) and not (
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    )
