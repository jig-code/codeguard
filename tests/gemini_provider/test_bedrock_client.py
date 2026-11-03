import asyncio

import pytest
from pydantic_ai.models.test import TestModel

from codeguard.gemini_provider import BedrockClaude, bedrock_client


@pytest.mark.parametrize(
    "model_id",
    [
        "us.anthropic.claude-haiku-5-5",
        "us.openai.gpt-6-luna",
        "arn:aws:bedrock:us-east-1:123456789012:inference-profile/us.openai.gpt-6-luna",
    ],
)
def test_converse_receives_the_selected_model_unchanged(monkeypatch, model_id):
    connected = []
    model = TestModel()

    def connect(name):
        connected.append(name)
        return model

    async def run():
        async with BedrockClaude()(model_id) as selected:
            assert selected is model

    monkeypatch.setattr(bedrock_client, "BedrockConverseModel", connect)
    asyncio.run(run())
    assert connected == [model_id]
