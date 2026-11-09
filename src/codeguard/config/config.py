from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from codeguard.config.judge_config import JudgeConfig
from codeguard.config.package_config import PackageConfig
from codeguard.config.versions import ExactVersion

# The only settings the environment may set: the judge, which CI names since it has no
# subscription. Every other setting decides what a review reports, so it stays in the
# committed config.
_ENVIRONMENT_JUDGE_KEYS = ("provider", "model")


class _JudgeEnvironment(EnvSettingsSource):
    """`CODEGUARD_JUDGE__PROVIDER` and `CODEGUARD_JUDGE__MODEL`, and no other variable."""

    def __call__(self) -> dict[str, object]:
        judge = super().__call__().get("judge")
        if not isinstance(judge, dict):
            return {}
        named = {key: judge[key] for key in _ENVIRONMENT_JUDGE_KEYS if key in judge}
        return {"judge": named} if named else {}


class Config(BaseSettings):
    """The project's settings: the values passed in, which ConfigLoader reads from the config
    file, under `CODEGUARD_JUDGE__PROVIDER` and `CODEGUARD_JUDGE__MODEL`."""

    model_config = SettingsConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,
        validate_by_name=True,
        env_prefix="CODEGUARD_",
        env_nested_delimiter="__",
        # An empty variable, as CI leaves one it can't fill, means nothing, like an unset one.
        env_ignore_empty=True,
    )

    confidence_threshold: float = Field(default=0.9, ge=0, le=1)
    review_time_limit_minutes: int = Field(default=5, ge=1)
    ast_grep: ExactVersion | None = Field(default=None, alias="ast-grep")
    packages: tuple[PackageConfig, ...] = ()
    judge: JudgeConfig = JudgeConfig()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (_JudgeEnvironment(settings_cls), init_settings)
