from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from pathlib import Path

import httpx2
from google.auth.exceptions import GoogleAuthError
from google.genai import Client
from google.genai.types import HttpOptions
from google.oauth2.service_account import Credentials
from pydantic import SecretStr
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


@dataclass(frozen=True)
class VertexGemini:
    settings: GeminiSettings
    transport: httpx2.AsyncBaseTransport | None = None

    @asynccontextmanager
    async def __call__(self, model: str) -> AsyncIterator[Model]:
        # Each judgement runs on its own event loop, so it gets its own HTTP client.
        async with create_async_httpx2_client(transport=self.transport) as http:
            with self._signed_in_provider(http) as provider:
                async with GoogleModel(model, provider=provider) as connected:
                    yield connected

    @contextmanager
    def _signed_in_provider(self, http: httpx2.AsyncClient) -> Iterator[GoogleCloudProvider]:
        settings = self.settings
        match settings.required_sign_in:
            case Path() as credentials_file:
                yield GoogleCloudProvider(
                    credentials=_credentials(credentials_file),
                    project=settings.required_project,
                    location=settings.location,
                    http_client=http,
                )
            case SecretStr() as api_key:
                # GoogleCloudProvider drops an API key given with a project, so the client that
                # keeps both is built here.
                with Client(
                    vertexai=True,
                    api_key=api_key.get_secret_value(),
                    project=settings.required_project,
                    location=settings.location,
                    http_options=HttpOptions(
                        headers={"User-Agent": get_user_agent()},
                        httpx_async_client=http,
                        timeout=DEFAULT_HTTP_TIMEOUT * 1000,
                    ),
                ) as client:
                    yield GoogleCloudProvider(client=client)


def _credentials(credentials_file: Path) -> Credentials:
    try:
        return Credentials.from_service_account_file(str(credentials_file))
    except (OSError, ValueError, GoogleAuthError) as error:
        raise JudgeProcessError(
            f"Gemini on Vertex AI couldn't read the service account key file {credentials_file}: "
            f"{type(error).__name__}"
        ) from error
