import asyncio
import os
from dataclasses import dataclass, field
from unittest import mock

import pytest
from google.auth.exceptions import DefaultCredentialsError
from google.genai import Client

from codeguard.gemini_provider import VertexGemini
from codeguard.review import JudgeProcessError


@dataclass
class RecordingClients:
    received: list[dict[str, object]] = field(default_factory=list)

    def __call__(self, **kwargs: object) -> Client:
        self.received.append(kwargs)
        return Client(**kwargs)


def _no_credentials(**_: object) -> Client:
    raise DefaultCredentialsError("no credentials found")


@pytest.fixture
def no_ambient_google_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("GOOGLE_API_KEY", "GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION"):
        monkeypatch.delenv(name, raising=False)


class TestVertexGeminiFromConfig:
    @mock.patch.dict(
        os.environ,
        {
            "GOOGLE_API_KEY": "proxy-injected",
            "GOOGLE_CLOUD_PROJECT": "env-project",
            "GOOGLE_CLOUD_LOCATION": "us",
        },
    )
    def test_api_key_project_and_location_come_from_the_environment(self):
        assert VertexGemini.from_config(None, None) == VertexGemini(
            project="env-project", location="us", api_key="proxy-injected"
        )

    @pytest.mark.usefixtures("no_ambient_google_env")
    @mock.patch.dict(
        os.environ, {"GOOGLE_CLOUD_PROJECT": "env-project", "GOOGLE_CLOUD_LOCATION": "us"}
    )
    def test_configured_project_and_location_win_over_the_environment(self):
        assert VertexGemini.from_config("sanctum", "eu") == VertexGemini(
            project="sanctum", location="eu", api_key=None
        )

    @pytest.mark.usefixtures("no_ambient_google_env")
    def test_location_defaults_to_global(self):
        assert VertexGemini.from_config(None, None) == VertexGemini(
            project=None, location="global", api_key=None
        )


class TestVertexGemini:
    def test_missing_google_credentials_are_a_judge_error(self):
        models = VertexGemini(project=None, location="global", api_key=None, genai=_no_credentials)

        async def connect() -> None:
            async with models("gemini-4-argon"):
                pass

        with pytest.raises(JudgeProcessError) as error:
            asyncio.run(connect())

        assert str(error.value) == (
            "Gemini on Vertex AI found no Google credentials: no credentials found"
        )

    def test_api_key_without_a_project_is_a_judge_error(self):
        clients = RecordingClients()
        models = VertexGemini(
            project=None, location="global", api_key="proxy-injected", genai=clients
        )

        async def connect() -> None:
            async with models("gemini-4-argon"):
                pass

        with pytest.raises(JudgeProcessError) as error:
            asyncio.run(connect())

        assert str(error.value) == (
            "Gemini on Vertex AI needs a project to run with an API key: set judge.project or "
            "GOOGLE_CLOUD_PROJECT."
        )
        assert clients.received == []
