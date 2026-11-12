from pydantic import Field
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from codeguard.config.config_error import ConfigError
from codeguard.config.judge_config import JudgeConfig
from codeguard.config.package_config import PackageConfig
from codeguard.config.versions import ExactVersion

_ENVIRONMENT_JUDGE_KEYS = ("provider", "model", "gemini")
_ENVIRONMENT_ONLY_JUDGE_KEYS = ("gemini",)


class _JudgeEnvironment(EnvSettingsSource):
    def __call__(self) -> dict[str, object]:
        judge = super().__call__().get("judge")
        if not isinstance(judge, dict):
            return {}
        named = {key: judge[key] for key in _ENVIRONMENT_JUDGE_KEYS if key in judge}
        return {"judge": named} if named else {}


class _ConfigFile(PydanticBaseSettingsSource):
    def __init__(self, settings_cls: type[BaseSettings], file: PydanticBaseSettingsSource) -> None:
        super().__init__(settings_cls)
        self.file = file

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[object, str, bool]:
        return None, field_name, False

    def __call__(self) -> dict[str, object]:
        settings = self.file()
        judge = settings.get("judge")
        if isinstance(judge, dict):
            for key in _ENVIRONMENT_ONLY_JUDGE_KEYS:
                if key in judge:
                    raise ConfigError(
                        f"judge.{key} is read from the environment only: set the "
                        f"CODEGUARD_JUDGE__{key.upper()}__ variables instead"
                    )
        return settings


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,
        validate_by_name=True,
        env_prefix="CODEGUARD_",
        env_nested_delimiter="__",
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
        return (_JudgeEnvironment(settings_cls), _ConfigFile(settings_cls, init_settings))
