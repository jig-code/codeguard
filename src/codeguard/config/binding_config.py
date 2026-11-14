from pathlib import Path

from pydantic import (
    BaseModel,
    ConfigDict,
    DirectoryPath,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from codeguard.config.change_kind import ChangeKind
from codeguard.config.judge_config import JudgeChoice, JudgeProvider
from codeguard.config.severity import Severity

SKILL_FILE = "SKILL.md"
# Released rule packages still set it, from when evals judged code variants.
_RETIRED_FIELDS = frozenset({"disable_skips"})


class BindingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    skill: DirectoryPath
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

    @field_validator("skill", mode="before")
    @classmethod
    def resolve_skill_in_working_tree(cls, skill: object, info: ValidationInfo) -> object:
        if not isinstance(skill, str | Path):
            return skill
        working_tree = (info.context or {}).get("working_tree", Path())
        return working_tree / skill

    @field_validator("skill")
    @classmethod
    def validate_skill_file_exists(cls, skill: Path) -> Path:
        if not (skill / SKILL_FILE).is_file():
            raise ValueError(f"{skill} has no {SKILL_FILE}")
        return skill
