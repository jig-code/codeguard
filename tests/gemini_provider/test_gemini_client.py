import asyncio

import pytest

from codeguard.config import KeyFileSignIn
from codeguard.gemini_provider import VertexGemini
from codeguard.review import JudgeProcessError


def test_unreadable_service_account_key_file_is_a_judge_error(tmp_path):
    key_file = tmp_path / "judge.json"
    models = VertexGemini(KeyFileSignIn("my-project", "global", key_file))

    async def connect() -> None:
        async with models("gemini-4-argon"):
            pass

    with pytest.raises(JudgeProcessError) as error:
        asyncio.run(connect())

    assert str(error.value) == (
        f"Gemini on Vertex AI couldn't read the service account key file {key_file}: "
        "FileNotFoundError"
    )
