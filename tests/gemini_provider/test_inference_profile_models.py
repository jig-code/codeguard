import boto3
import pytest
from botocore.stub import Stubber

from codeguard.gemini_provider import InferenceProfileModels
from codeguard.review import JudgeProcessError

ARN = "arn:aws:bedrock:us-west-2:123456789012:application-inference-profile/a1b2c3"
HAIKU = "us.anthropic.claude-haiku-5-5"


@pytest.fixture
def bedrock(monkeypatch) -> Stubber:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    client = boto3.client("bedrock", region_name="us-west-2")
    with Stubber(client) as stubber:
        yield stubber


def profiles(stubber: Stubber) -> InferenceProfileModels:
    return InferenceProfileModels(client=lambda region: stubber.client)


def tagged(stubber: Stubber, *tags: dict[str, str]) -> None:
    stubber.add_response("list_tags_for_resource", {"tags": list(tags)}, {"resourceARN": ARN})


class TestInferenceProfileModels:
    def test_model_is_the_profile_model_id_tag(self, bedrock):
        tagged(bedrock, {"key": "team", "value": "codeguard"}, {"key": "ModelId", "value": HAIKU})

        assert profiles(bedrock).model_of(ARN) == HAIKU

    def test_tag_is_read_once_per_profile(self, bedrock):
        tagged(bedrock, {"key": "ModelId", "value": HAIKU})
        models = profiles(bedrock)
        models.model_of(ARN)

        assert models.model_of(ARN) == HAIKU
        bedrock.assert_no_pending_responses()

    def test_profile_without_the_tag_is_a_judge_error(self, bedrock):
        tagged(bedrock, {"key": "team", "value": "codeguard"})

        with pytest.raises(JudgeProcessError) as error:
            profiles(bedrock).model_of(ARN)

        assert str(error.value) == (
            f"The inference profile {ARN} has no ModelId tag naming its model"
        )

    def test_unreadable_tags_are_a_judge_error(self, bedrock):
        bedrock.add_client_error("list_tags_for_resource", "AccessDeniedException", "denied")

        with pytest.raises(JudgeProcessError) as error:
            profiles(bedrock).model_of(ARN)

        assert str(error.value).startswith(
            f"Could not read the ModelId tag of the inference profile {ARN}: "
        )
