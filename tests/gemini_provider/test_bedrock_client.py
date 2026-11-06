import pytest

from codeguard.config import ConfigError
from codeguard.gemini_provider import BedrockClaude

ARN = "arn:aws:bedrock:us-west-2:123456789012:application-inference-profile/a1b2c3"
HAIKU = "us.anthropic.claude-haiku-5-5"


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-west-2")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")


def unreachable(model):
    raise AssertionError("no tag read expected")


def in_region(region):
    return BedrockClaude(profile_model=unreachable, region=lambda: region)


class TestBedrockClaude:
    @pytest.mark.parametrize(
        ("region", "profile"),
        [
            ("us-west-2", "us.anthropic.claude-haiku-5-5"),
            ("eu-central-1", "eu.anthropic.claude-haiku-5-5"),
            ("ap-northeast-1", "apac.anthropic.claude-haiku-5-5"),
            ("us-gov-west-1", "us-gov.anthropic.claude-haiku-5-5"),
        ],
    )
    def test_vendor_id_runs_as_the_inference_profile_of_the_region(self, region, profile):
        assert in_region(region).model("claude-haiku-5-5").model_name == profile

    def test_gpt_model_runs_as_its_openai_profile(self):
        assert in_region("us-east-1").model("gpt-6-luna").model_name == "us.openai.gpt-6-luna"

    def test_region_comes_from_the_aws_configuration(self, monkeypatch):
        monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-1")
        monkeypatch.setenv("AWS_REGION", "eu-west-1")

        model = BedrockClaude(profile_model=unreachable).model("claude-haiku-5-5")

        assert model.model_name == "eu.anthropic.claude-haiku-5-5"

    def test_vendor_id_without_a_region_is_an_error(self):
        with pytest.raises(ConfigError) as error:
            in_region(None).model("claude-haiku-5-5")

        assert str(error.value) == (
            "Bedrock needs an AWS region for a model named by its vendor's id: set AWS_REGION"
        )

    def test_region_without_inference_profiles_is_an_error(self):
        with pytest.raises(ConfigError) as error:
            in_region("me-south-1").model("claude-haiku-5-5")

        assert str(error.value) == "Bedrock has no cross-region inference profiles for me-south-1"

    @pytest.mark.parametrize(
        "model",
        [
            HAIKU,
            "anthropic.claude-haiku-5-5",
            "arn:aws:bedrock:us-west-2:123456789012:inference-profile/us.anthropic.claude-haiku-5-5",
        ],
    )
    def test_bedrock_id_passes_through_without_an_aws_call(self, model):
        bedrock_model = in_region(None).model(model)

        assert bedrock_model.model_name == model
        assert "bedrock_inference_profile" not in (bedrock_model.settings or {})

    def test_application_profile_runs_as_its_tagged_model(self):
        bedrock_model = BedrockClaude(profile_model={ARN: HAIKU}.__getitem__).model(ARN)

        assert bedrock_model.model_name == HAIKU
        assert bedrock_model.settings == {"bedrock_inference_profile": ARN}
        assert bedrock_model.profile.get("bedrock_supports_tool_choice")
