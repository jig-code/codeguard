from pydantic import Field, ValidationError
from pydantic_core import InitErrorDetails, PydanticCustomError
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from codeguard.config.judge_config import GeminiSettings, JudgeConfig
from codeguard.config.package_config import PackageConfig
from codeguard.config.versions import ExactVersion

_ENV_PREFIX = "CODEGUARD_"
_ENV_NESTED_DELIMITER = "__"
_GEMINI = "gemini"
_ENVIRONMENT_ONLY_JUDGE_KEYS = (_GEMINI,)
_ENVIRONMENT_JUDGE_KEYS = ("provider", "model", *_ENVIRONMENT_ONLY_JUDGE_KEYS)


class _JudgeEnvironment(EnvSettingsSource):
    def __call__(self) -> dict[str, object]:
        judge = super().__call__().get("judge")
        if not isinstance(judge, dict):
            return {}
        named = {key: judge[key] for key in _ENVIRONMENT_JUDGE_KEYS if key in judge}
        return {"judge": named} if named else {}


class _ConfigFile(PydanticBaseSettingsSource):
    """The config file's settings, which may not hold the judge settings only the environment
    sets. pydantic-settings merges the environment's values over the file's, so the file's are
    checked here, before the merge can hide them."""

    def __init__(self, settings_cls: type[BaseSettings], file: PydanticBaseSettingsSource) -> None:
        super().__init__(settings_cls)
        self.file = file

    def get_field_value(self, field: object, field_name: str) -> tuple[object, str, bool]:
        return None, field_name, False

    def __call__(self) -> dict[str, object]:
        settings = self.file()
        judge = settings.get("judge")
        errors = [
            InitErrorDetails(
                type=PydanticCustomError(
                    "environment_only", "read from the environment only, not the config file"
                ),
                loc=("judge", key),
                input=None,
            )
            for key in _ENVIRONMENT_ONLY_JUDGE_KEYS
            if isinstance(judge, dict) and key in judge
        ]
        if errors:
            raise ValidationError.from_exception_data(self.settings_cls.__name__, errors)
        return settings


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,
        validate_by_name=True,
        env_prefix=_ENV_PREFIX,
        env_nested_delimiter=_ENV_NESTED_DELIMITER,
        env_ignore_empty=True,
        hide_input_in_errors=True,
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


def gemini_variable(field: str) -> str:
    """The environment variable that sets `judge.gemini.<field>`."""
    if field not in GeminiSettings.model_fields:
        raise KeyError(field)
    return _ENV_PREFIX + _ENV_NESTED_DELIMITER.join(("judge", _GEMINI, field)).upper()
