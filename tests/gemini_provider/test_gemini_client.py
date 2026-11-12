import asyncio
from pathlib import Path

import pytest
from pydantic import SecretStr

from codeguard.config import ConfigError, GeminiSettings
from codeguard.gemini_provider import VertexGemini
from codeguard.review import JudgeProcessError


class TestVertexGemini:
    @pytest.mark.parametrize(
        ("settings", "error_type", "message"),
        [
            (
                GeminiSettings(api_key=SecretStr("proxy-injected")),
                ConfigError,
                "Gemini needs a project: set CODEGUARD_JUDGE__GEMINI__PROJECT",
            ),
            (
                GeminiSettings(project="my-project"),
                ConfigError,
                "Gemini needs a way to sign in: set CODEGUARD_JUDGE__GEMINI__API_KEY or "
                "CODEGUARD_JUDGE__GEMINI__CREDENTIALS_FILE",
            ),
            (
                GeminiSettings(project="my-project", credentials_file=Path("judge.json")),
                JudgeProcessError,
                "Gemini on Vertex AI couldn't read the service account key file judge.json: "
                "FileNotFoundError",
            ),
        ],
        ids=["no project", "no sign-in", "missing credentials file"],
    )
    def test_unusable_settings_fail_the_call(
        self, tmp_path, monkeypatch, settings, error_type, message
    ):
        monkeypatch.chdir(tmp_path)
        models = VertexGemini(settings)

        async def connect() -> None:
            async with models("gemini-4-argon"):
                pass

        with pytest.raises(error_type) as error:
            asyncio.run(connect())

        assert str(error.value) == message
