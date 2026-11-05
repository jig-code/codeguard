import boto3
import pytest
from botocore.stub import Stubber

from codeguard.gemini_provider import bedrock_client
from codeguard.gemini_provider.bedrock_client import BedrockClaude, application_profile_model
from codeguard.review import JudgeProcessError

ARN = "arn:aws:bedrock:us-west-2:123456789012:application-inference-profile/a1b2c3"
HAIKU = "us.anthropic.claude-haiku-5-5"


@pytest.fixture(autouse=True)
def aws_region(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-west-2")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    application_profile_model.cache_clear()


@pytest.fixture
def bedrock(monkeypatch) -> Stubber:
    client = boto3.client("bedrock", region_name="us-west-2")
    monkeypatch.setattr(bedrock_client.boto3, "client", lambda *args, **kwargs: client)
    with Stubber(client) as stubber:
        yield stubber


class TestBedrockClaude:
    def test_model_id_is_sent_as_its_name(self):
        model = BedrockClaude().model(HAIKU)

        assert model.model_name == HAIKU
        assert "bedrock_inference_profile" not in (model.settings or {})

    def test_application_profile_runs_as_the_model_it_routes_to(self):
        model = BedrockClaude(profile_model=lambda arn: HAIKU).model(ARN)

        assert model.model_name == HAIKU
        assert model.settings == {"bedrock_inference_profile": ARN}
        assert model.profile.get("bedrock_supports_tool_choice")


class TestApplicationProfileModel:
    def test_reads_the_model_the_profile_routes_to(self, bedrock):
        bedrock.add_response(
            "get_inference_profile",
            {
                "inferenceProfileName": "codeguard-haiku",
                "inferenceProfileArn": ARN,
                "inferenceProfileId": "a1b2c3",
                "status": "ACTIVE",
                "type": "APPLICATION",
                "models": [
                    {
                        "modelArn": "arn:aws:bedrock:us-west-2::foundation-model/"
                        "anthropic.claude-haiku-5-5"
                    }
                ],
            },
            {"inferenceProfileIdentifier": ARN},
        )

        assert application_profile_model(ARN) == "anthropic.claude-haiku-5-5"

    def test_unreadable_profile_is_a_judge_error(self, bedrock):
        bedrock.add_client_error("get_inference_profile", "AccessDeniedException", "denied")

        with pytest.raises(JudgeProcessError) as error:
            application_profile_model(ARN)

        assert str(error.value).startswith(f"Could not read the inference profile {ARN}: ")
