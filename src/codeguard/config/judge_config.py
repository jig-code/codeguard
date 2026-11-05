import os
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from codeguard.config.config_error import ConfigError

# Gemini's and Bedrock's pay-as-you-go capacity is shared, so fewer calls at once keep a run
# under its tokens-per-minute limit.
_API_CALLS_AT_ONCE = 2
# Bedrock names a model by its vendor and the vendor's id, so a vendor's ids are told apart by
# their prefix.
_BEDROCK_VENDORS = {"claude-": "anthropic", "gpt-": "openai"}
_CLAUDE_PREFIX = "claude-"


class JudgeProvider(StrEnum):
    CLAUDE_CLI = "claude-cli"
    GEMINI = "gemini"
    BEDROCK = "bedrock"
    CODEX_CLI = "codex-cli"

    @property
    def runs_a_cli(self) -> bool:
        """A CLI has a default model of its own; an API needs one named."""
        return self in (JudgeProvider.CLAUDE_CLI, JudgeProvider.CODEX_CLI)


class JudgeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: JudgeProvider
    # None runs a CLI with no model named, so its own default judges.
    name: str | None = None

    @property
    def label(self) -> str:
        return self.name or f"{self.provider}'s default model"


class JudgeChoice(BaseModel):
    """One level's choice of judge: a binding's, the project's or a rule package's. The
    provider and the model each come from the first level that names it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: JudgeProvider | None = None
    model: str | None = None

    def over(self, fallback: "JudgeChoice") -> "JudgeChoice":
        return JudgeChoice(
            provider=self.provider or fallback.provider, model=self.model or fallback.model
        )

    @property
    def judge_model(self) -> JudgeModel:
        """The judge this choice names: with no provider named, the claude CLI, which runs
        only Claude models."""
        if self.provider is None and self.model and not self.model.startswith(_CLAUDE_PREFIX):
            raise ConfigError(
                f"model {self.model} needs a provider: set provider in the rule's binding, "
                "judge.provider in .codeguard/config.yaml (or CODEGUARD_JUDGE__PROVIDER), or "
                "judge.provider in its package's codeguard-package.yaml"
            )
        return JudgeModel(provider=self.provider or JudgeProvider.CLAUDE_CLI, name=self.model)


class BedrockConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    # The cross-region inference profile's prefix, such as us, eu or global.
    inference_prefix: str = "us"

    def model_id(self, model: str) -> str:
        """The id Bedrock runs a model by: a Claude or GPT model named by its vendor's id maps
        to its cross-region inference profile; any other id, such as an application
        inference profile's ARN, is Bedrock's own and passes through as is."""
        vendors = [
            vendor for prefix, vendor in _BEDROCK_VENDORS.items() if model.startswith(prefix)
        ]
        return f"{self.inference_prefix}.{vendors[0]}.{model}" if vendors else model


class JudgeConfig(BaseModel):
    """The project's `judge`: its default choice of judge, and the settings that stay
    global."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: JudgeProvider | None = None
    model: str | None = None
    bedrock: BedrockConfig = BedrockConfig()
    project: str | None = None
    location: str | None = None
    calls_at_once: int | None = Field(default=None, ge=1)

    @property
    def choice(self) -> JudgeChoice:
        return JudgeChoice(provider=self.provider, model=self.model)

    def concurrency(self, provider: JudgeProvider) -> int:
        if provider is JudgeProvider.GEMINI and self.calls_at_once is not None:
            return self.calls_at_once
        if not provider.runs_a_cli:
            return _API_CALLS_AT_ONCE
        return os.process_cpu_count() or 1
