import asyncio
from pathlib import Path

import pytest
from pydantic import SecretStr

from codeguard.config import GeminiSettings
from codeguard.gemini_provider import VertexGemini
from codeguard.review import JudgeProcessError


class TestVertexGemini:
    @pytest.mark.parametrize(
        ("settings", "message"),
        [
            (
                GeminiSettings(api_key=SecretStr("proxy-injected")),
                "Gemini on Vertex AI needs CODEGUARD_JUDGE__GEMINI__PROJECT.",
            ),
            (
                GeminiSettings(project="my-project"),
                "Gemini on Vertex AI needs CODEGUARD_JUDGE__GEMINI__API_KEY or "
                "CODEGUARD_JUDGE__GEMINI__CREDENTIALS_FILE.",
            ),
            (
                GeminiSettings(project="my-project", credentials_file=Path("judge.json")),
                "Gemini on Vertex AI couldn't read the service account key file judge.json: "
                "FileNotFoundError",
            ),
        ],
        ids=["no project", "no sign-in", "missing credentials file"],
    )
    def test_unusable_settings_are_a_judge_error(self, tmp_path, monkeypatch, settings, message):
        monkeypatch.chdir(tmp_path)
        models = VertexGemini(settings)

        async def connect() -> None:
            async with models("gemini-4-argon"):
                pass

        with pytest.raises(JudgeProcessError) as error:
            asyncio.run(connect())

        assert str(error.value) == message
