from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass

import httpx2
from google.auth.exceptions import GoogleAuthError
from google.genai import Client
from google.genai.types import HttpOptions
from google.oauth2.service_account import Credentials
from pydantic_ai.models import (
    DEFAULT_HTTP_TIMEOUT,
    Model,
    create_async_httpx2_client,
    get_user_agent,
)
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google_cloud import GoogleCloudProvider

from codeguard.config import GeminiSettings
from codeguard.review import JudgeProcessError

_CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


@dataclass(frozen=True)
class VertexGemini:
    settings: GeminiSettings
    client_factory: Callable[..., Client] = Client
    transport: httpx2.AsyncBaseTransport | None = None

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
        settings = self.settings
        if settings.project is None:
            raise JudgeProcessError(
                "Gemini on Vertex AI needs a project: set CODEGUARD_JUDGE__GEMINI__PROJECT."
            )
        if settings.api_key is None and settings.credentials_file is None:
            raise JudgeProcessError(
                "Gemini on Vertex AI needs a way to sign in: set CODEGUARD_JUDGE__GEMINI__API_KEY "
                "or CODEGUARD_JUDGE__GEMINI__CREDENTIALS_FILE."
            )
        return self.client_factory(
            vertexai=True,
            api_key=None if settings.api_key is None else settings.api_key.get_secret_value(),
            credentials=self._credentials(),
            project=settings.project,
            location=settings.location,
            http_options=HttpOptions(
                headers={"User-Agent": get_user_agent()},
                httpx_async_client=http,
                timeout=DEFAULT_HTTP_TIMEOUT * 1000,
            ),
        )

    def _credentials(self) -> Credentials | None:
        path = self.settings.credentials_file
        if path is None:
            return None
        try:
            return Credentials.from_service_account_file(str(path), scopes=[_CLOUD_PLATFORM_SCOPE])
        except (OSError, ValueError, GoogleAuthError) as error:
            raise JudgeProcessError(
                f"Gemini on Vertex AI couldn't read the service account key file {path}: "
                f"{type(error).__name__}"
            ) from error
