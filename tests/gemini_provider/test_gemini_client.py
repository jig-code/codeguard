import asyncio
from dataclasses import dataclass, field

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


def test_missing_google_credentials_are_a_judge_error():
    models = VertexGemini(
        project="my-project", location="global", api_key=None, genai=_no_credentials
    )

    with pytest.raises(JudgeProcessError) as error:
        asyncio.run(models("gemini-4-argon").__aenter__())

    assert str(error.value) == (
        "Gemini on Vertex AI found no Google credentials: no credentials found"
    )


def test_client_is_built_with_the_api_key_project_and_location():
    clients = RecordingClients()
    models = VertexGemini(
        project="my-project", location="us", api_key="proxy-injected", genai=clients
    )

    asyncio.run(models("gemini-4-argon").__aenter__())

    assert clients.received == [
        {"vertexai": True, "api_key": "proxy-injected", "project": "my-project", "location": "us"}
    ]
