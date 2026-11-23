from collections.abc import Iterable
from enum import StrEnum
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, SecretStr
from pydantic_ai.settings import ThinkingEffort
from pydantic_settings import BaseSettings, SettingsConfigDict

from codeguard.config.config_error import ConfigError

ClaudeEffort = Literal["low", "medium", "high", "xhigh", "max"]
CodexEffort = Literal["low", "medium", "high"]
ApiEffort = ThinkingEffort
ClaudeEffortOrDefault = Literal["default", ClaudeEffort]
CodexEffortOrDefault = Literal["default", CodexEffort]
ApiEffortOrDefault = Literal["default", ApiEffort]

# Gemini's and Bedrock's pay-as-you-go capacity is shared, so fewer calls at once keep a run
# under its tokens-per-minute limit.
_API_CALLS_AT_ONCE = 2


class ModelFamily(StrEnum):
    CLAUDE = "claude-"
    GPT = "gpt-"
    GEMINI = "gemini-"

    @classmethod
    def of(cls, model: str) -> "ModelFamily | None":
        return next((family for family in cls if model.startswith(family)), None)


class JudgeProvider(StrEnum):
    CLAUDE_CLI = "claude-cli"
    GEMINI = "gemini"
    BEDROCK = "bedrock"
    CODEX_CLI = "codex-cli"

    @property
    def default_model(self) -> str | None:
        return _DEFAULT_MODELS[self]

    @property
    def runs_a_cli(self) -> bool:
        return self in (JudgeProvider.CLAUDE_CLI, JudgeProvider.CODEX_CLI)

    @property
    def families(self) -> frozenset[ModelFamily]:
        return _FAMILIES[self]


# The models codeguard was tested with on each provider.
_DEFAULT_MODELS = {
    JudgeProvider.CLAUDE_CLI: None,
    JudgeProvider.CODEX_CLI: "gpt-6-luna",
    JudgeProvider.GEMINI: "gemini-4-argon",
    JudgeProvider.BEDROCK: "us.anthropic.claude-haiku-5-5",
}


_FAMILIES = {
    JudgeProvider.CLAUDE_CLI: frozenset({ModelFamily.CLAUDE}),
    JudgeProvider.CODEX_CLI: frozenset({ModelFamily.GPT}),
    JudgeProvider.GEMINI: frozenset({ModelFamily.GEMINI}),
    JudgeProvider.BEDROCK: frozenset({ModelFamily.CLAUDE, ModelFamily.GPT}),
}


def _unset(key: str, problem: str) -> ConfigError:
    return ConfigError(
        f"{problem}: set {key} in the rule's binding, judge.{key} in .codeguard/config.yaml "
        f"(or CODEGUARD_JUDGE__{key.upper()}), or judge.{key} in its package's "
        "codeguard-package.yaml"
    )


class JudgeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: JudgeProvider
    name: str | None = None

    @property
    def label(self) -> str:
        return self.name or f"{self.provider}'s default model"

    @property
    def required_name(self) -> str:
        if self.name is None:
            raise _unset("model", f"provider {self.provider} needs a model")
        return self.name


class JudgeChoice(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: JudgeProvider | None = None
    model: str | None = None

    def over(self, fallback: "JudgeChoice") -> "JudgeChoice":
        return JudgeChoice(
            provider=self.provider or fallback.provider, model=self.model or fallback.model
        )

    @property
    def judge_model(self) -> JudgeModel:
        family = ModelFamily.of(self.model) if self.model else None
        if self.provider is None and self.model and family is not ModelFamily.CLAUDE:
            raise _unset("provider", f"model {self.model} needs a provider")
        provider = self.provider or JudgeProvider.CLAUDE_CLI
        if family is not None and family not in provider.families:
            raise ConfigError(f"provider {provider} can't run model {self.model}")
        if self.model is None and provider is not JudgeProvider.CLAUDE_CLI:
            raise _unset("model", f"provider {provider} needs a model")
        return JudgeModel(provider=provider, name=self.model)


class GeminiSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CODEGUARD_JUDGE__GEMINI__", frozen=True, env_ignore_empty=True
    )

    project: str | None = None
    location: str = "global"
    api_key: SecretStr | None = None
    credentials_file: Path | None = None

    def require_sign_in_for(self, models: Iterable[JudgeModel]) -> None:
        if any(model.provider is JudgeProvider.GEMINI for model in models):
            self._check_sign_in()

    def _check_sign_in(self) -> None:
        if self.project is None:
            raise ConfigError("Gemini needs a project: set CODEGUARD_JUDGE__GEMINI__PROJECT")
        if self.api_key is None and self.credentials_file is None:
            raise ConfigError(
                "Gemini needs a way to sign in: set CODEGUARD_JUDGE__GEMINI__API_KEY or "
                "CODEGUARD_JUDGE__GEMINI__CREDENTIALS_FILE"
            )
        if self.api_key is not None and self.credentials_file is not None:
            raise ConfigError(
                "Gemini needs one way to sign in: set CODEGUARD_JUDGE__GEMINI__API_KEY or "
                "CODEGUARD_JUDGE__GEMINI__CREDENTIALS_FILE, not both"
            )


class ThinkingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, validate_by_name=True)

    claude_cli: ClaudeEffortOrDefault = Field(default="default", alias="claude-cli")
    codex_cli: CodexEffortOrDefault = Field(default="default", alias="codex-cli")
    gemini: ApiEffortOrDefault = "medium"
    bedrock: ApiEffortOrDefault = "medium"


def sent_effort[Effort: str](setting: Effort | Literal["default"]) -> Effort | None:
    return None if setting == "default" else cast("Effort", setting)


class JudgeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: JudgeProvider | None = None
    model: str | None = None
    calls_at_once: int | None = Field(default=None, ge=1)
    request_time_limit_seconds: int = Field(default=120, ge=1)
    thinking: ThinkingConfig = ThinkingConfig()

    @property
    def choice(self) -> JudgeChoice:
        return JudgeChoice(provider=self.provider, model=self.model)

    def concurrency(self, provider: JudgeProvider, cpus: int | None) -> int:
        """How many calls a provider makes at once, given the machine's CPU count, which
        may be unknown."""
        if provider.runs_a_cli:
            return cpus or 1
        return self.calls_at_once or _API_CALLS_AT_ONCE
