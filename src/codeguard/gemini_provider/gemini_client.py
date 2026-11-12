from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from pathlib import Path

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

from codeguard.config import GeminiSettings, gemini_variable
from codeguard.review import JudgeProcessError


@dataclass(frozen=True)
class VertexGemini:
    settings: GeminiSettings
    transport: httpx2.AsyncBaseTransport | None = None

    @asynccontextmanager
    async def __call__(self, model: str) -> AsyncIterator[Model]:
        # Each judgement runs on its own event loop, so it gets its own HTTP client.
        project = self._project()
        async with create_async_httpx2_client(transport=self.transport) as http:
            with self._signed_in_provider(project, http) as provider:
                async with GoogleModel(model, provider=provider) as connected:
                    yield connected

    def _project(self) -> str:
        if self.settings.project is None:
            raise JudgeProcessError(f"Gemini on Vertex AI needs {gemini_variable('project')}.")
        return self.settings.project

    @contextmanager
    def _signed_in_provider(
        self, project: str, http: httpx2.AsyncClient
    ) -> Iterator[GoogleCloudProvider]:
        settings = self.settings
        if settings.credentials_file is not None:
            yield GoogleCloudProvider(
                credentials=_credentials(settings.credentials_file),
                project=project,
                location=settings.location,
                http_client=http,
            )
        elif settings.api_key is not None:
            # GoogleCloudProvider drops an API key given with a project, so the client that
            # keeps both is built here.
            with Client(
                vertexai=True,
                api_key=settings.api_key.get_secret_value(),
                project=project,
                location=settings.location,
                http_options=HttpOptions(
                    headers={"User-Agent": get_user_agent()},
                    httpx_async_client=http,
                    timeout=DEFAULT_HTTP_TIMEOUT * 1000,
                ),
            ) as client:
                yield GoogleCloudProvider(client=client)
        else:
            raise JudgeProcessError(
                f"Gemini on Vertex AI needs {gemini_variable('api_key')} or "
                f"{gemini_variable('credentials_file')}."
            )


def _credentials(credentials_file: Path) -> Credentials:
    try:
        return Credentials.from_service_account_file(str(credentials_file))
    except (OSError, ValueError, GoogleAuthError) as error:
        raise JudgeProcessError(
            f"Gemini on Vertex AI couldn't read the service account key file {credentials_file}: "
            f"{type(error).__name__}"
        ) from error
