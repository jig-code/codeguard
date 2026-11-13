from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from pathlib import Path

import httpx2
from google.auth.exceptions import GoogleAuthError
from google.genai import Client
from google.genai.types import HttpOptions
from google.oauth2.service_account import Credentials
from pydantic_ai.models import Model, create_async_httpx2_client
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google_cloud import GoogleCloudProvider

from codeguard.config import GeminiSettings
from codeguard.review import JudgeProcessError

_CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


@dataclass(frozen=True)
class VertexGemini:
    settings: GeminiSettings
    transport: httpx2.AsyncBaseTransport | None = None

    @asynccontextmanager
    async def __call__(self, model: str) -> AsyncIterator[Model]:
        # Each judgement runs on its own event loop, so it gets its own HTTP client.
        async with create_async_httpx2_client(transport=self.transport) as http:
            with self._client(http) as client:
                yield GoogleModel(model, provider=GoogleCloudProvider(client=client))

    # GoogleCloudProvider can't send an API key together with a project, so codeguard builds
    # the client for every sign-in.
    @contextmanager
    def _client(self, http: httpx2.AsyncClient) -> Iterator[Client]:
        settings = self.settings
        settings.check_sign_in()
        with Client(
            vertexai=True,
            api_key=settings.api_key.get_secret_value() if settings.api_key else None,
            credentials=_credentials(settings.credentials_file)
            if settings.credentials_file
            else None,
            project=settings.project,
            location=settings.location,
            http_options=HttpOptions(httpx_async_client=http),
        ) as client:
            yield client


def _credentials(credentials_file: Path) -> Credentials:
    try:
        return Credentials.from_service_account_file(
            str(credentials_file), scopes=[_CLOUD_PLATFORM_SCOPE]
        )
    except (OSError, ValueError, GoogleAuthError) as error:
        raise JudgeProcessError(
            f"Gemini on Vertex AI couldn't read the service account key file {credentials_file}: "
            f"{type(error).__name__}"
        ) from error
