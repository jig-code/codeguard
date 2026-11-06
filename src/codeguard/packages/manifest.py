from pathlib import Path
from typing import Self

import yaml
from packaging.specifiers import SpecifierSet
from packaging.version import Version
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from codeguard.config import ConfigError, JudgeChoice, VersionRange

MANIFEST_FILE = "codeguard-package.yaml"


class Manifest(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, arbitrary_types_allowed=True, validate_by_name=True
    )

    name: str = Field(pattern=r"^[\w.-]+$")
    rulesets: tuple[str, ...] = Field(min_length=1)
    ast_grep: VersionRange = Field(default_factory=SpecifierSet, alias="ast-grep")
    codeguard: VersionRange = Field(default_factory=SpecifierSet)
    judge: JudgeChoice = JudgeChoice()

    @classmethod
    def load(cls, root: Path) -> Self:
        file = root / MANIFEST_FILE
        if not file.is_file():
            raise ConfigError(f"{root} has no {MANIFEST_FILE}")
        try:
            return cls.model_validate(yaml.safe_load(file.read_text()))
        except ValidationError as error:
            raise ConfigError.invalid(file, error) from error

    @classmethod
    def in_repo(cls, root: Path) -> Self | None:
        return cls.load(root) if (root / MANIFEST_FILE).is_file() else None

    def ast_grep_problem(self, version: Version) -> str | None:
        if self.ast_grep.contains(version, prereleases=True):
            return None
        return f"{self.name} supports ast-grep {self.ast_grep}, not {version}"

    def codeguard_problem(self, version: Version) -> str | None:
        if self.codeguard.contains(version, prereleases=True):
            return None
        return f"{self.name} needs codeguard {self.codeguard}, not {version}; upgrade codeguard"
