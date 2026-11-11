import asyncio
from dataclasses import dataclass, field

import pytest
from google.auth.exceptions import DefaultCredentialsError
from google.genai import Client
from pydantic_ai.providers.google_cloud import GoogleCloudProvider

from codeguard.gemini_provider import VertexGemini
from codeguard.review import JudgeProcessError


@dataclass
class RecordingClients:
    received: list[dict[str, object]] = field(default_factory=list)

    def __call__(self, **kwargs: object) -> Client:
        self.received.append(kwargs)
        return Client(**kwargs)


@pytest.fixture
def api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "proxy-injected")
    for name in ("GEMINI_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS"):
        monkeypatch.delenv(name, raising=False)


def test_missing_google_credentials_are_a_judge_error(monkeypatch):
    for name in ("GOOGLE_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(name, raising=False)

    def no_credentials(**_: str) -> GoogleCloudProvider:
        raise DefaultCredentialsError("no credentials found")

    models = VertexGemini(project="my-project", location="global", cloud=no_credentials)

    with pytest.raises(JudgeProcessError) as error:
        asyncio.run(models("gemini-3.1-pro-preview").__aenter__())

    assert str(error.value) == (
        "Gemini on Vertex AI found no Google credentials: no credentials found"
    )


@pytest.mark.usefixtures("api_key")
def test_api_key_is_sent_with_the_project_and_location_from_the_environment(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "my-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us")
    clients = RecordingClients()

    asyncio.run(VertexGemini(genai=clients)("gemini-3.1-pro-preview").__aenter__())

    assert clients.received == [
        {"vertexai": True, "api_key": "proxy-injected", "project": "my-project", "location": "us"}
    ]


@pytest.mark.usefixtures("api_key")
def test_api_key_without_a_location_runs_in_the_global_location(monkeypatch):
    for name in ("GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION"):
        monkeypatch.delenv(name, raising=False)
    clients = RecordingClients()

    asyncio.run(VertexGemini(genai=clients)("gemini-3.1-pro-preview").__aenter__())

    assert clients.received == [
        {"vertexai": True, "api_key": "proxy-injected", "project": None, "location": "global"}
    ]
