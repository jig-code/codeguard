import os
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Gemini's and Bedrock's pay-as-you-go capacity is shared, so fewer calls at once keep a run
# under its tokens-per-minute limit.
_API_CALLS_AT_ONCE = 2
# A rule is judged with the model its evals pass on, so only its binding names one.
_RETIRED_FIELDS = {
    "provider": "a rule's binding names its provider",
    "model": "a rule's binding names its model",
}


class JudgeProvider(StrEnum):
    CLAUDE_CLI = "claude-cli"
    GEMINI = "gemini"
    BEDROCK = "bedrock"
    CODEX_CLI = "codex-cli"

    @property
    def default_model(self) -> str:
        return _DEFAULT_MODELS[self]


# The models codeguard was tested with on each provider.
_DEFAULT_MODELS = {
    JudgeProvider.CLAUDE_CLI: "claude-sonnet-5-5",
    JudgeProvider.CODEX_CLI: "gpt-6-luna",
    JudgeProvider.GEMINI: "gemini-3.1-pro-preview",
    JudgeProvider.BEDROCK: "us.anthropic.claude-haiku-5-5",
}


class JudgeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: JudgeProvider
    name: str


class JudgeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    project: str | None = None
    location: str | None = None
    calls_at_once: int | None = Field(default=None, ge=1)

    @model_validator(mode="before")
    @classmethod
    def reject_retired_fields(cls, data: object) -> object:
        if isinstance(data, dict):
            retired = [f"judge.{key}: {why}" for key, why in _RETIRED_FIELDS.items() if key in data]
            if retired:
                raise ValueError("; ".join(retired))
        return data

    def concurrency(self, provider: JudgeProvider) -> int:
        if provider is JudgeProvider.GEMINI and self.calls_at_once is not None:
            return self.calls_at_once
        if provider not in (JudgeProvider.CLAUDE_CLI, JudgeProvider.CODEX_CLI):
            return _API_CALLS_AT_ONCE
        return os.process_cpu_count() or 1
