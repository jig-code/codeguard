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
from codeguard.config.languages import LANGUAGES, covers_language
from codeguard.config.severity import Severity

SKILL_FILE = "SKILL.md"
# A skill's language supplements are named after their language: `python.md`.
_SUPPLEMENT_SUFFIX = ".md"
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

    @property
    def supplements(self) -> dict[str, Path]:
        """The skill's supplement for each language: that language's forms of the convention."""
        return {
            file.stem: file
            for file in sorted(self.skill.glob(f"*{_SUPPLEMENT_SUFFIX}"))
            if file.name != SKILL_FILE
        }

    @model_validator(mode="after")
    def validate_supplements(self) -> Self:
        for language, file in self.supplements.items():
            if language not in LANGUAGES:
                raise ValueError(
                    f"{file} names no language codeguard knows; a supplement is one of: "
                    + ", ".join(f"{name}{_SUPPLEMENT_SUFFIX}" for name in LANGUAGES)
                )
            if not covers_language(self.paths, language):
                raise ValueError(f"{file} is for {language}, but paths match no {language} file")
        return self
