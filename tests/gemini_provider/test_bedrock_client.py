import pytest

from codeguard.gemini_provider import BedrockClaude, InferenceProfileModels

ARN = "arn:aws:bedrock:us-west-2:123456789012:application-inference-profile/a1b2c3"
HAIKU = "us.anthropic.claude-haiku-5-5"


@pytest.fixture(autouse=True)
def aws_region(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-west-2")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")


def unreachable(region):
    raise AssertionError("no AWS call expected")


class TestBedrockClaude:
    @pytest.mark.parametrize(
        "model",
        [
            HAIKU,
            "anthropic.claude-haiku-5-5",
            "arn:aws:bedrock:us-west-2:123456789012:inference-profile/us.anthropic.claude-haiku-5-5",
        ],
    )
    def test_recognised_id_passes_through_without_an_aws_call(self, model):
        bedrock_model = BedrockClaude(InferenceProfileModels(client=unreachable)).model(model)

        assert bedrock_model.model_name == model
        assert "bedrock_inference_profile" not in (bedrock_model.settings or {})

    def test_application_profile_runs_as_its_tagged_model(self):
        profiles = InferenceProfileModels(models={ARN: HAIKU})

        bedrock_model = BedrockClaude(profiles).model(ARN)

        assert bedrock_model.model_name == HAIKU
        assert bedrock_model.settings == {"bedrock_inference_profile": ARN}
        assert bedrock_model.profile.get("bedrock_supports_tool_choice")
