import asyncio
import os
from unittest import mock

import pytest
from google.auth.exceptions import DefaultCredentialsError
from pydantic_ai.providers.google_cloud import GoogleCloudProvider

from codeguard.gemini_provider import VertexGemini
from codeguard.review import JudgeProcessError


def test_missing_google_credentials_are_a_judge_error(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    def no_credentials(**_: str) -> GoogleCloudProvider:
        raise DefaultCredentialsError("no credentials found")

    models = VertexGemini(project="my-project", location="global", cloud=no_credentials)

    with pytest.raises(JudgeProcessError) as error:
        asyncio.run(models("gemini-4-argon").__aenter__())

    assert str(error.value) == (
        "Gemini on Vertex AI found no Google credentials: no credentials found"
    )


@mock.patch.dict(os.environ, {"GOOGLE_API_KEY": "proxy-injected"})
def test_api_key_without_a_project_is_a_judge_error(monkeypatch):
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)

    with pytest.raises(JudgeProcessError) as error:
        asyncio.run(VertexGemini()("gemini-4-argon").__aenter__())

    assert str(error.value) == (
        "Gemini on Vertex AI needs a project to use with the API key: set judge.project in "
        ".codeguard/config.yaml or GOOGLE_CLOUD_PROJECT"
    )
