from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from codeguard.config.config_error import ConfigError

# Gemini's and Bedrock's pay-as-you-go capacity is shared, so fewer calls at once keep a run
# under its tokens-per-minute limit.
_API_CALLS_AT_ONCE = 2


class ModelFamily(StrEnum):
    """A vendor's models, told apart by the prefix of the id the vendor gives them."""

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
    def runs_a_cli(self) -> bool:
        """A CLI has a default model of its own; an API needs one named."""
        return self in (JudgeProvider.CLAUDE_CLI, JudgeProvider.CODEX_CLI)

    @property
    def families(self) -> frozenset[ModelFamily]:
        return _FAMILIES[self]


# The vendors' models each provider runs. A model of no known family, such as a Bedrock
# application inference profile's ARN, is the provider's own id.
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
    # None runs a CLI with no model named, so its own default judges.
    name: str | None = None

    @property
    def label(self) -> str:
        return self.name or f"{self.provider}'s default model"

    @property
    def api_name(self) -> str:
        """The model an API provider runs, which has no default of its own."""
        if self.name is None:
            raise _unset("model", f"provider {self.provider} needs a model")
        return self.name


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
        """The judge this choice names: with no provider named, the claude CLI. A model of
        a family the provider can't run is an error."""
        family = ModelFamily.of(self.model) if self.model else None
        if self.provider is None and self.model and family is not ModelFamily.CLAUDE:
            raise _unset("provider", f"model {self.model} needs a provider")
        provider = self.provider or JudgeProvider.CLAUDE_CLI
        if family is not None and family not in provider.families:
            raise ConfigError(f"provider {provider} can't run model {self.model}")
        return JudgeModel(provider=provider, name=self.model)


class JudgeConfig(BaseModel):
    """The project's `judge`: its default choice of judge, and the settings that stay
    global."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: JudgeProvider | None = None
    model: str | None = None
    project: str | None = None
    location: str | None = None
    calls_at_once: int | None = Field(default=None, ge=1)

    @property
    def choice(self) -> JudgeChoice:
        return JudgeChoice(provider=self.provider, model=self.model)

    def concurrency(self, provider: JudgeProvider, cpus: int | None) -> int:
        """How many calls a provider makes at once, given the machine's CPU count, which
        may be unknown."""
        if provider is JudgeProvider.GEMINI and self.calls_at_once is not None:
            return self.calls_at_once
        if not provider.runs_a_cli:
            return _API_CALLS_AT_ONCE
        return cpus or 1
