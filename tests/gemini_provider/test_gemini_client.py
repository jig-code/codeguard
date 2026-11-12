import asyncio
import os
from unittest import mock

import pytest

from codeguard.config import JudgeProvider
from codeguard.gemini_provider import VertexGemini
from codeguard.review import JudgeProcessError

MODEL = JudgeProvider.GEMINI.default_model


def test_missing_google_credentials_are_a_judge_error(tmp_path, monkeypatch):
    key_file = tmp_path / "judge.json"
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(key_file))
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)

    with pytest.raises(JudgeProcessError) as error:
        asyncio.run(VertexGemini()(MODEL).__aenter__())

    assert str(error.value) == (
        f"Gemini on Vertex AI found no Google credentials: File {key_file} was not found."
    )


@mock.patch.dict(os.environ, {"GOOGLE_API_KEY": "proxy-injected"})
def test_api_key_without_a_project_is_a_judge_error(monkeypatch):
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)

    with pytest.raises(JudgeProcessError) as error:
        asyncio.run(VertexGemini()(MODEL).__aenter__())

    assert str(error.value) == (
        "Gemini on Vertex AI needs a project to use with the API key: set judge.project in "
        ".codeguard/config.yaml or GOOGLE_CLOUD_PROJECT"
    )
