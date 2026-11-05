import re
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import cache

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from pydantic_ai.models import Model
from pydantic_ai.models.bedrock import BedrockConverseModel, BedrockModelSettings

from codeguard.review import JudgeProcessError

# An application inference profile's ARN ends in an id that names no model.
_APPLICATION_PROFILE = re.compile(
    r"^arn:[^:]+:bedrock:(?P<region>[^:]*):[^:]*:application-inference-profile/"
)


@cache
def application_profile_model(arn: str) -> str:
    """The Bedrock id of the model an application inference profile routes to, read from
    Bedrock's control plane, which judges nothing."""
    match = _APPLICATION_PROFILE.match(arn)
    region = match["region"] if match else None
    try:
        profile = boto3.client("bedrock", region_name=region).get_inference_profile(
            inferenceProfileIdentifier=arn
        )
    except (BotoCoreError, ClientError) as error:
        raise JudgeProcessError(f"Could not read the inference profile {arn}: {error}") from error
    return profile["models"][0]["modelArn"].rsplit("/", 1)[-1]


# Claude or GPT on Amazon Bedrock, by the id Bedrock runs it by. boto3 finds the region and
# credentials as the AWS CLI does.
@dataclass(frozen=True)
class BedrockClaude:
    profile_model: Callable[[str], str] = application_profile_model

    @asynccontextmanager
    async def __call__(self, model: str) -> AsyncIterator[Model]:
        yield self.model(model)

    def model(self, model: str) -> BedrockConverseModel:
        """The model pydantic-ai runs. An application inference profile's ARN tells
        pydantic-ai nothing about the model behind it, so pydantic-ai gets that model's id,
        which decides how it calls the model, and sends the ARN as the request's model id."""
        if not _APPLICATION_PROFILE.match(model):
            return BedrockConverseModel(model)
        return BedrockConverseModel(
            self.profile_model(model),
            settings=BedrockModelSettings(bedrock_inference_profile=model),
        )
