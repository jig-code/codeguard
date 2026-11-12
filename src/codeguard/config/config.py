from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from codeguard.config.judge_config import FromEnvironment, JudgeConfig
from codeguard.config.package_config import PackageConfig
from codeguard.config.versions import ExactVersion

_ENVIRONMENT_JUDGE_KEYS = ("provider", "model")
_ENVIRONMENT_ONLY_JUDGE_KEY = "gemini"


class _JudgeEnvironment(EnvSettingsSource):
    def __call__(self) -> dict[str, object]:
        judge = super().__call__().get("judge")
        if not isinstance(judge, dict):
            return {}
        named = {key: judge[key] for key in _ENVIRONMENT_JUDGE_KEYS if key in judge}
        if _ENVIRONMENT_ONLY_JUDGE_KEY in judge:
            named[_ENVIRONMENT_ONLY_JUDGE_KEY] = FromEnvironment(judge[_ENVIRONMENT_ONLY_JUDGE_KEY])
        return {"judge": named} if named else {}


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,
        validate_by_name=True,
        env_prefix="CODEGUARD_",
        env_nested_delimiter="__",
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
        return (_JudgeEnvironment(settings_cls), init_settings)
