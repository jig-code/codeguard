from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
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
        project = self._project()
        match self._sign_in():
            case Path() as key_file:
                provider = GoogleCloudProvider(
                    credentials=_credentials(key_file),
                    project=project,
                    location=self.settings.location,
                )
                async with GoogleModel(model, provider=provider) as connected:
                    yield connected
            case api_key:
                async with self._signed_in_by_key(model, project, api_key) as connected:
                    yield connected

    def _project(self) -> str:
        if self.settings.project is None:
            raise JudgeProcessError("Gemini on Vertex AI needs judge.gemini.project.")
        return self.settings.project

    def _sign_in(self) -> Path | SecretStr:
        match self.settings.api_key, self.settings.credentials_file:
            case None, None:
                raise JudgeProcessError(
                    "Gemini on Vertex AI needs judge.gemini.api_key or "
                    "judge.gemini.credentials_file."
                )
            case None, Path() as key_file:
                return key_file
            case SecretStr() as api_key, None:
                return api_key
            case _:
                raise JudgeProcessError(
                    "Gemini on Vertex AI signs in with judge.gemini.api_key or "
                    "judge.gemini.credentials_file, not both."
                )

    # GoogleCloudProvider drops an API key given with a project, so the client that keeps
    # both is built here, sending through httpx2 as the provider's own client does.
    @asynccontextmanager
    async def _signed_in_by_key(
        self, model: str, project: str, api_key: SecretStr
    ) -> AsyncIterator[Model]:
        async with create_async_httpx2_client(transport=self.transport) as http:
            with Client(
                vertexai=True,
                api_key=api_key.get_secret_value(),
                project=project,
                location=self.settings.location,
                http_options=HttpOptions(
                    headers={"User-Agent": get_user_agent()},
                    httpx_async_client=http,
                    timeout=DEFAULT_HTTP_TIMEOUT * 1000,
                ),
            ) as client:
                yield GoogleModel(model, provider=GoogleCloudProvider(client=client))


def _credentials(key_file: Path) -> Credentials:
    try:
        return Credentials.from_service_account_file(str(key_file))
    except (OSError, ValueError, GoogleAuthError) as error:
        raise JudgeProcessError(
            f"Gemini on Vertex AI couldn't read the service account key file {key_file}: "
            f"{type(error).__name__}"
        ) from error
