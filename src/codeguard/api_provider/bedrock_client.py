from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Literal

from pydantic_ai.models import Model
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydantic_ai.providers.bedrock import BedrockProvider


# Claude on Amazon Bedrock, for the judge where a run must be Claude. boto3 finds the region
# and credentials as the AWS CLI does.
@dataclass(frozen=True)
class BedrockClaude:
    provider: Literal["bedrock"] | BedrockProvider = "bedrock"

    @asynccontextmanager
    async def __call__(self, model: str) -> AsyncIterator[Model]:
        yield BedrockConverseModel(model, provider=self.provider)
