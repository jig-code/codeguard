import asyncio

import pytest
from pydantic import SecretStr

from codeguard.config import GeminiSettings
from codeguard.gemini_provider import VertexGemini
from codeguard.review import JudgeProcessError


class TestVertexGemini:
    @pytest.mark.parametrize(
        ("project", "api_key", "key_file", "message"),
        [
            (
                None,
                SecretStr("proxy-injected"),
                None,
                "Gemini on Vertex AI needs judge.gemini.project.",
            ),
            (
                "my-project",
                None,
                None,
                "Gemini on Vertex AI needs judge.gemini.api_key or judge.gemini.credentials_file.",
            ),
            (
                "my-project",
                SecretStr("proxy-injected"),
                "judge.json",
                "Gemini on Vertex AI signs in with judge.gemini.api_key or "
                "judge.gemini.credentials_file, not both.",
            ),
            (
                "my-project",
                None,
                "judge.json",
                "Gemini on Vertex AI couldn't read the service account key file {key_file}: "
                "FileNotFoundError",
            ),
        ],
        ids=["no project", "no sign-in", "two sign-ins", "missing key file"],
    )
    def test_unusable_settings_are_a_judge_error(
        self, tmp_path, project, api_key, key_file, message
    ):
        credentials_file = None if key_file is None else tmp_path / key_file
        models = VertexGemini(
            GeminiSettings(project=project, api_key=api_key, credentials_file=credentials_file)
        )

        async def connect() -> None:
            async with models("gemini-4-argon"):
                pass

        with pytest.raises(JudgeProcessError) as error:
            asyncio.run(connect())

        assert str(error.value) == message.format(key_file=credentials_file)
