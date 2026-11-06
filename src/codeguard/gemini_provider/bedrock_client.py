from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass

from boto3.session import Session
from pydantic_ai.models import Model
from pydantic_ai.models.bedrock import BedrockConverseModel, BedrockModelSettings
from pydantic_ai.providers.bedrock import BEDROCK_GEO_PREFIXES

from codeguard.config import ConfigError, ModelFamily
from codeguard.gemini_provider.inference_profile_models import (
    application_profile_model,
    is_application_profile,
)

# Bedrock names a vendor's model by the vendor's name and its id.
_VENDORS = {ModelFamily.CLAUDE: "anthropic", ModelFamily.GPT: "openai"}
# Bedrock's cross-region inference profiles are named for a geography, where an AWS region's
# name starts with its own: `us-west-2` is in `us`, `ap-northeast-1` in `apac`.
_GEOGRAPHIES = {"ap": "apac"}


def _region() -> str | None:
    """The region the standard AWS configuration names, as boto3 finds it."""
    return Session().region_name


def geography(region: str | None) -> str:
    """The geography whose cross-region inference profiles run models in an AWS region."""
    if region is None:
        raise ConfigError(
            "Bedrock needs an AWS region for a model named by its vendor's id: set AWS_REGION"
        )
    name = "us-gov" if region.startswith("us-gov-") else region.split("-")[0]
    name = _GEOGRAPHIES.get(name, name)
    if name not in BEDROCK_GEO_PREFIXES:
        raise ConfigError(f"Bedrock has no cross-region inference profiles for {region}")
    return name


# Claude or GPT on Amazon Bedrock. boto3 finds the region and credentials as the AWS CLI does.
@dataclass(frozen=True)
class BedrockClaude:
    profile_model: Callable[[str], str] = application_profile_model
    region: Callable[[], str | None] = _region

    @asynccontextmanager
    async def __call__(self, model: str) -> AsyncIterator[Model]:
        yield self.model(model)

    def model(self, model: str) -> BedrockConverseModel:
        """The model pydantic-ai runs. A vendor's id runs as its inference profile in the
        configured region; any other id is Bedrock's own and passes through, except that an
        application inference profile's ARN names no model, so pydantic-ai gets the model
        its tag names and sends the ARN as the model id."""
        if is_application_profile(model):
            return BedrockConverseModel(
                self.profile_model(model),
                settings=BedrockModelSettings(bedrock_inference_profile=model),
            )
        family = ModelFamily.of(model)
        vendor = _VENDORS.get(family) if family else None
        if vendor:
            return BedrockConverseModel(f"{geography(self.region())}.{vendor}.{model}")
        return BedrockConverseModel(model)
