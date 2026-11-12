import asyncio
import os
from unittest import mock

import pytest
from google.auth.exceptions import DefaultCredentialsError
from google.genai import Client

from codeguard.gemini_provider import VertexGemini
from codeguard.review import JudgeProcessError


def _no_credentials(**_: object) -> Client:
    raise DefaultCredentialsError("no credentials found")


def _no_client(**_: object) -> Client:
    raise AssertionError


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
    @pytest.mark.parametrize(
        ("models", "message"),
        [
            (
                VertexGemini(
                    project=None,
                    location="global",
                    api_key=None,
                    client_factory=_no_credentials,
                ),
                "Gemini on Vertex AI found no Google credentials: no credentials found",
            ),
            (
                VertexGemini(
                    project=None,
                    location="global",
                    api_key="proxy-injected",
                    client_factory=_no_client,
                ),
                "Gemini on Vertex AI needs a project to run with an API key: set judge.project "
                "or GOOGLE_CLOUD_PROJECT.",
            ),
        ],
        ids=["missing credentials", "api key without a project"],
    )
    def test_unusable_google_settings_are_a_judge_error(self, models, message):
        async def connect() -> None:
            async with models("gemini-4-argon"):
                pass

        with pytest.raises(JudgeProcessError) as error:
            asyncio.run(connect())

        assert str(error.value) == message
