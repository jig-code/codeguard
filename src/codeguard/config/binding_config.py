from pathlib import Path
from typing import Self

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
from codeguard.config.retired_keys import without_retired_keys
from codeguard.config.severity import Severity

LEGACY_SKILL_FILE = "SKILL.md"
# Released rule packages still set it, from when evals judged code variants.
_RETIRED_FIELDS = frozenset({"disable_skips"})


class BindingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rule: str | None = None
    skill: DirectoryPath | None = None
    paths: tuple[str, ...] = Field(min_length=1)
    exclude_paths: tuple[str, ...] = ()
    severity: Severity = Severity.ERROR
    provider: JudgeProvider | None = None
    model: str | None = None
    triggers: frozenset[str] = Field(frozenset({ChangeKind.ANY}), min_length=1)

    @property
    def judge(self) -> JudgeChoice:
        return JudgeChoice(provider=self.provider, model=self.model)

    @property
    def is_legacy_skill(self) -> bool:
        return self.skill is not None

    @property
    def rule_id(self) -> str:
        if self.skill is not None:
            return self.skill.name
        assert self.rule is not None
        return self.rule

    @model_validator(mode="before")
    @classmethod
    def drop_retired_fields(cls, data: object) -> object:
        return without_retired_keys(data, _RETIRED_FIELDS)

    @model_validator(mode="after")
    def validate_one_rule(self) -> Self:
        if self.rule is not None and self.skill is not None:
            raise ValueError("rule and skill both name a rule: keep only rule")
        if self.rule is None and self.skill is None:
            raise ValueError("name the rule with rule: <id>")
        return self

    @field_validator("skill", mode="before")
    @classmethod
    def resolve_skill_in_working_tree(cls, skill: object, info: ValidationInfo) -> object:
        if not isinstance(skill, str | Path):
            return skill
        working_tree = (info.context or {}).get("working_tree", Path())
        return working_tree / skill

    @field_validator("skill")
    @classmethod
    def validate_skill_file_exists(cls, skill: Path | None) -> Path | None:
        if skill is not None and not (skill / LEGACY_SKILL_FILE).is_file():
            raise ValueError(f"{skill} has no {LEGACY_SKILL_FILE}")
        return skill
