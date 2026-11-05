from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from pydantic_ai.models import Model
from pydantic_ai.models.bedrock import BedrockConverseModel, BedrockModelSettings

from codeguard.gemini_provider.inference_profile_models import (
    InferenceProfileModels,
    is_application_profile,
)


# Claude or GPT on Amazon Bedrock, by the id Bedrock runs it by. boto3 finds the region and
# credentials as the AWS CLI does.
@dataclass(frozen=True)
class BedrockClaude:
    profiles: InferenceProfileModels

    @asynccontextmanager
    async def __call__(self, model: str) -> AsyncIterator[Model]:
        yield self.model(model)

    def model(self, model: str) -> BedrockConverseModel:
        """The model pydantic-ai runs. An id pydantic-ai recognises passes through. An
        application inference profile's ARN names no model, so pydantic-ai gets the model its
        tag names, which decides how it calls the model, and sends the ARN as the model id."""
        if not is_application_profile(model):
            return BedrockConverseModel(model)
        return BedrockConverseModel(
            self.profiles.model_of(model),
            settings=BedrockModelSettings(bedrock_inference_profile=model),
        )
