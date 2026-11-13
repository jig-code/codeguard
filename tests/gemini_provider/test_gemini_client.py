import asyncio

import pytest

from codeguard.config import GeminiSettings
from codeguard.gemini_provider import VertexGemini
from codeguard.review import JudgeProcessError


def test_unreadable_service_account_key_file_is_a_judge_error(tmp_path):
    key_file = tmp_path / "judge.json"
    models = VertexGemini(GeminiSettings(project="my-project", credentials_file=key_file))

    async def connect() -> None:
        async with models("gemini-judge-test"):
            pass

    with pytest.raises(JudgeProcessError) as error:
        asyncio.run(connect())

    assert str(error.value) == (
        f"Gemini on Vertex AI couldn't read the service account key file {key_file}: "
        "FileNotFoundError"
    )
