from contextlib import nullcontext

import boto3
import pytest
from botocore.stub import Stubber
from pydantic_ai.providers.bedrock import BedrockProvider

from codeguard.api_provider import ApiJudge, BedrockClaude
from codeguard.config import JudgeModel, JudgeProvider, ThinkingConfig, sent_effort
from codeguard.review import JudgeProcessError


def test_default_model_is_asked_for_the_verdict_as_strict_native_output(
    tmp_path, make_judge_request
):
    client = boto3.client(
        "bedrock-runtime",
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )
    sent: list[dict[str, object]] = []
    client.meta.events.register(
        "provide-client-params.bedrock-runtime.ConverseStream",
        lambda params, **_: sent.append(params),
    )
    stubber = Stubber(client)
    stubber.add_client_error("converse_stream", http_status_code=400)
    default = JudgeModel(provider=JudgeProvider.BEDROCK, name=JudgeProvider.BEDROCK.default_model)
    judge = ApiJudge(
        tmp_path,
        default.required_name,
        BedrockClaude(BedrockProvider(bedrock_client=client)),
        nullcontext(),
        default.provider,
        sent_effort(ThinkingConfig().bedrock),
    )

    with stubber, pytest.raises(JudgeProcessError):
        judge.judge(make_judge_request())

    [request] = sent
    tools = request["toolConfig"]["tools"]
    assert [tool["toolSpec"]["name"] for tool in tools] == [
        "read_file",
        "search_files",
        "list_files",
    ]
    output = request["outputConfig"]["textFormat"]
    assert (output["type"], output["structure"]["jsonSchema"]["name"]) == ("json_schema", "Verdict")
