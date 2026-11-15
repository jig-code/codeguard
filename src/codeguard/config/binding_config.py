from pydantic import BaseModel, ConfigDict, Field, model_validator

from codeguard.config.change_kind import ChangeKind
from codeguard.config.judge_config import JudgeChoice, JudgeProvider
from codeguard.config.severity import Severity

# Released rule packages still set it, from when evals judged code variants.
_RETIRED_FIELDS = frozenset({"disable_skips"})
_SKILL_KEY = "skill"


class BindingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rule: str
    paths: tuple[str, ...] = Field(min_length=1)
    exclude_paths: tuple[str, ...] = ()
    severity: Severity = Severity.ERROR
    provider: JudgeProvider | None = None
    model: str | None = None
    triggers: frozenset[str] = Field(frozenset({ChangeKind.ANY}), min_length=1)

    @property
    def judge(self) -> JudgeChoice:
        return JudgeChoice(provider=self.provider, model=self.model)

    @model_validator(mode="before")
    @classmethod
    def drop_retired_fields(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        return {key: value for key, value in data.items() if key not in _RETIRED_FIELDS}

    @model_validator(mode="before")
    @classmethod
    def reject_skill(cls, data: object) -> object:
        if isinstance(data, dict) and _SKILL_KEY in data:
            raise ValueError(
                "skill is no longer supported: move the rule to rules/judge/<id>.md "
                "and name it with rule: <id>"
            )
        return data
