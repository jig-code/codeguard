import asyncio
from pathlib import Path

import pytest
from google.genai import Client
from pydantic import SecretStr

from codeguard.config import GeminiSettings
from codeguard.gemini_provider import VertexGemini
from codeguard.review import JudgeProcessError


def _no_client(**_: object) -> Client:
    raise AssertionError


class TestVertexGemini:
    @pytest.mark.parametrize(
        ("settings", "message"),
        [
            (
                GeminiSettings(api_key=SecretStr("proxy-injected")),
                "Gemini on Vertex AI needs a project: set CODEGUARD_JUDGE__GEMINI__PROJECT.",
            ),
            (
                GeminiSettings(project="my-project"),
                "Gemini on Vertex AI needs a way to sign in: set CODEGUARD_JUDGE__GEMINI__API_KEY "
                "or CODEGUARD_JUDGE__GEMINI__CREDENTIALS_FILE.",
            ),
            (
                GeminiSettings(project="my-project", credentials_file=Path("missing/judge.json")),
                "Gemini on Vertex AI couldn't read the service account key file "
                "missing/judge.json: FileNotFoundError",
            ),
        ],
        ids=["no project", "no sign-in", "missing key file"],
    )
    def test_unusable_settings_are_a_judge_error(self, settings, message):
        models = VertexGemini(settings, client_factory=_no_client)

        async def connect() -> None:
            async with models("gemini-4-argon"):
                pass

        with pytest.raises(JudgeProcessError) as error:
            asyncio.run(connect())

        assert str(error.value) == message
