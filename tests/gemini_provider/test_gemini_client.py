import asyncio

import pytest
from google.auth.exceptions import DefaultCredentialsError
from pydantic_ai.providers.google_cloud import GoogleCloudProvider

from codeguard.gemini_provider import VertexGemini
from codeguard.review import JudgeProcessError


def test_missing_google_credentials_are_a_judge_error():
    def no_credentials(**_: str) -> GoogleCloudProvider:
        raise DefaultCredentialsError("no credentials found")

    models = VertexGemini(project="my-project", location="global", cloud=no_credentials)

    with pytest.raises(JudgeProcessError) as error:
        asyncio.run(models("gemini-3.1-pro-preview").__aenter__())

    assert str(error.value) == (
        "Gemini on Vertex AI found no Google credentials: no credentials found"
    )
