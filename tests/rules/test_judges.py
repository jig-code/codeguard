import os
from unittest import mock

import pytest
from diskcache import Cache

from codeguard.claude_provider import ClaudeJudge
from codeguard.codex_provider import CodexJudge
from codeguard.config import JudgeConfig, JudgeModel, JudgeProvider
from codeguard.gemini_provider import GeminiJudge, VertexGemini
from codeguard.rules.judges import Judges


@pytest.fixture
def no_ambient_google_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
    ):
        monkeypatch.delenv(name, raising=False)


class TestJudges:
    def test_every_judge_shares_the_store_process_limit_and_warmup(self, tmp_path):
        judges = Judges(store=Cache(tmp_path))

        cached = judges.cached(
            tmp_path, JudgeModel(provider=JudgeProvider.CLAUDE_CLI, name="sonnet")
        )
        uncached = judges.uncached(
            tmp_path, JudgeModel(provider=JudgeProvider.CLAUDE_CLI, name="opus")
        )

        assert isinstance(cached.wrapped, ClaudeJudge)
        assert isinstance(uncached, ClaudeJudge)
        assert cached.store is judges.store
        assert cached.wrapped.processes is uncached.processes
        assert uncached.processes is judges.processes[JudgeProvider.CLAUDE_CLI]
        assert cached.wrapped.warmup is uncached.warmup is judges.warmup

    def test_gemini_model_builds_a_gemini_judge_with_its_name(self, tmp_path):
        judges = Judges(JudgeConfig(project="sanctum"), store=Cache(tmp_path))
        model = JudgeModel(provider=JudgeProvider.GEMINI, name="gemini-3.1-pro-preview")

        judge = judges.uncached(tmp_path, model)

        assert isinstance(judge, GeminiJudge)
        assert judge.model == "gemini-3.1-pro-preview"
        assert judge.processes is judges.processes[JudgeProvider.GEMINI]

    @pytest.mark.usefixtures("no_ambient_google_env")
    @mock.patch.dict(
        os.environ,
        {
            "GOOGLE_API_KEY": "proxy-injected",
            "GOOGLE_CLOUD_PROJECT": "env-project",
            "GOOGLE_CLOUD_LOCATION": "us",
        },
    )
    def test_gemini_judge_runs_with_the_api_key_project_and_location_from_the_environment(
        self, tmp_path
    ):
        judges = Judges(store=Cache(tmp_path))
        model = JudgeModel(provider=JudgeProvider.GEMINI, name="gemini-4-argon")

        judge = judges.uncached(tmp_path, model)

        assert judge == GeminiJudge(
            tmp_path,
            "gemini-4-argon",
            VertexGemini(project="env-project", location="us", api_key="proxy-injected"),
            judges.processes[JudgeProvider.GEMINI],
        )

    @pytest.mark.usefixtures("no_ambient_google_env")
    @mock.patch.dict(
        os.environ, {"GOOGLE_CLOUD_PROJECT": "env-project", "GOOGLE_CLOUD_LOCATION": "us"}
    )
    def test_gemini_project_and_location_from_the_config_win_over_the_environment(self, tmp_path):
        judges = Judges(JudgeConfig(project="sanctum", location="eu"), store=Cache(tmp_path))
        model = JudgeModel(provider=JudgeProvider.GEMINI, name="gemini-4-argon")

        judge = judges.uncached(tmp_path, model)

        assert judge == GeminiJudge(
            tmp_path,
            "gemini-4-argon",
            VertexGemini(project="sanctum", location="eu", api_key=None),
            judges.processes[JudgeProvider.GEMINI],
        )

    @pytest.mark.usefixtures("no_ambient_google_env")
    def test_gemini_location_defaults_to_global(self, tmp_path):
        judges = Judges(store=Cache(tmp_path))
        model = JudgeModel(provider=JudgeProvider.GEMINI, name="gemini-4-argon")

        judge = judges.uncached(tmp_path, model)

        assert judge == GeminiJudge(
            tmp_path,
            "gemini-4-argon",
            VertexGemini(project=None, location="global", api_key=None),
            judges.processes[JudgeProvider.GEMINI],
        )

    def test_bedrock_model_builds_a_judge_cached_apart_from_gemini(self, tmp_path):
        judges = Judges(store=Cache(tmp_path))
        model = JudgeModel(provider=JudgeProvider.BEDROCK, name="us.anthropic.claude-haiku-5-5")

        judge = judges.uncached(tmp_path, model)

        assert isinstance(judge, GeminiJudge)
        assert judge.identity == "bedrock\0us.anthropic.claude-haiku-5-5"
        assert judge.processes is judges.processes[JudgeProvider.BEDROCK]


def test_codex_binding_builds_a_separate_subscription_judge(tmp_path):
    judges = Judges(store=Cache(tmp_path))
    model = JudgeModel(provider=JudgeProvider.CODEX_CLI, name="gpt-6-luna")

    judge = judges.uncached(tmp_path, model)

    assert isinstance(judge, CodexJudge)
    assert judge.model == model.name
    assert judge.processes is judges.processes[JudgeProvider.CODEX_CLI]
    assert (
        judge.identity
        != judges.uncached(
            tmp_path, JudgeModel(provider=JudgeProvider.BEDROCK, name=model.name)
        ).identity
    )


def test_bedrock_accepts_a_gpt_inference_profile_without_changing_the_backend(tmp_path):
    judges = Judges(store=Cache(tmp_path))
    model = JudgeModel(provider=JudgeProvider.BEDROCK, name="us.openai.gpt-6-luna")

    judge = judges.uncached(tmp_path, model)

    assert isinstance(judge, GeminiJudge)
    assert judge.identity == "bedrock\0us.openai.gpt-6-luna"
