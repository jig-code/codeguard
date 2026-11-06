import asyncio

import pytest

from codeguard.gemini_provider import VertexGemini
from codeguard.review import JudgeProcessError

GOOGLE_CREDENTIALS = (
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_CLOUD_LOCATION",
    "CLOUDSDK_CONFIG",
)


@pytest.fixture
def no_google_credentials(monkeypatch, tmp_path):
    for name in GOOGLE_CREDENTIALS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("NO_GCE_CHECK", "True")


async def connect(models: VertexGemini) -> None:
    async with models("gemini-3.1-pro-preview"):
        pass


@pytest.mark.usefixtures("no_google_credentials")
def test_missing_google_credentials_are_a_judge_error():
    with pytest.raises(JudgeProcessError) as error:
        asyncio.run(connect(VertexGemini()))

    assert str(error.value).startswith("Gemini on Vertex AI found no Google credentials: ")
