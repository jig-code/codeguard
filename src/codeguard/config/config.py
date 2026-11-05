from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from codeguard.config.judge_config import JudgeConfig
from codeguard.config.package_config import PackageConfig
from codeguard.config.versions import ExactVersion


class Config(BaseSettings):
    """The project's settings: the values passed in, which ConfigLoader reads from the config
    file, under the environment. An environment variable named after a key overrides them:
    `CODEGUARD_JUDGE__MODEL` is `judge.model`."""

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
        return (env_settings, init_settings)
