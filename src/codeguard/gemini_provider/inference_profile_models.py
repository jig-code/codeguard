import re
from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock

import boto3
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from codeguard.review import JudgeProcessError

# An application inference profile's ARN ends in an id that names no model, so pydantic-ai can't
# tell which model it runs.
_APPLICATION_PROFILE = re.compile(
    r"^arn:[^:]+:bedrock:(?P<region>[^:]*):[^:]*:application-inference-profile/"
)
# The tag on an application inference profile that names the Bedrock model it routes to.
MODEL_ID_TAG = "ModelId"


def is_application_profile(model: str) -> bool:
    return _APPLICATION_PROFILE.match(model) is not None


def _bedrock_client(region: str | None) -> BaseClient:
    return boto3.client("bedrock", region_name=region or None)


@dataclass
class InferenceProfileModels:
    """The model each application inference profile routes to, read from its `ModelId` tag
    once per profile in a process."""

    client: Callable[[str | None], BaseClient] = _bedrock_client
    models: dict[str, str] = field(default_factory=dict)
    lock: Lock = field(default_factory=Lock)

    def model_of(self, arn: str) -> str:
        with self.lock:
            if arn not in self.models:
                self.models[arn] = self._tagged_model(arn)
            return self.models[arn]

    def _tagged_model(self, arn: str) -> str:
        match = _APPLICATION_PROFILE.match(arn)
        try:
            response = self.client(match["region"] if match else None).list_tags_for_resource(
                resourceARN=arn
            )
        except (BotoCoreError, ClientError) as error:
            raise JudgeProcessError(
                f"Could not read the {MODEL_ID_TAG} tag of the inference profile {arn}: {error}"
            ) from error
        models = [tag["value"] for tag in response.get("tags", []) if tag["key"] == MODEL_ID_TAG]
        if not models:
            raise JudgeProcessError(
                f"The inference profile {arn} has no {MODEL_ID_TAG} tag naming its model"
            )
        return models[0]
