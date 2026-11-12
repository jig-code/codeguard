import re
from functools import cache

import boto3
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


@cache
def application_profile_model(arn: str) -> str:
    """The model an application inference profile routes to, read from its `ModelId` tag
    once per profile in a process."""
    match = _APPLICATION_PROFILE.match(arn)
    client = boto3.client("bedrock", region_name=(match["region"] if match else None) or None)
    try:
        response = client.list_tags_for_resource(resourceARN=arn)
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
