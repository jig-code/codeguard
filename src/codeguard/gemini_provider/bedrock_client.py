from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from pydantic_ai.models import Model
from pydantic_ai.models.bedrock import BedrockConverseModel, BedrockModelSettings


# Claude or GPT on Amazon Bedrock. boto3 finds the region and credentials as the AWS CLI does.
@dataclass(frozen=True)
class BedrockClaude:
    # An application inference profile's ARN, which requests send in place of the model.
    inference_profile: str | None = None

    @asynccontextmanager
    async def __call__(self, model: str) -> AsyncIterator[Model]:
        settings = (
            BedrockModelSettings(bedrock_inference_profile=self.inference_profile)
            if self.inference_profile
            else None
        )
        yield BedrockConverseModel(model, settings=settings)
