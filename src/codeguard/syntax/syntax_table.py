from collections.abc import Mapping
from enum import StrEnum
from functools import cache
from pathlib import Path, PurePath
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, field_validator

from codeguard.config import ChangeKind, GateRule

_LANGUAGES_DIR = Path(__file__).parent / "languages"

type AstGrepRule = dict[str, object]


class NodeKind(StrEnum):
    COMMENT = "comments"
    IMPORT = "imports"
    NAME = "names"
    DEFINITION = "definitions"
    SCOPE = "scopes"
    SCOPE_NAME = "scope_names"


class SyntaxTable(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    language: str
    extensions: tuple[str, ...]
    comments: AstGrepRule
    imports: AstGrepRule
    names: AstGrepRule
    definitions: AstGrepRule
    scopes: AstGrepRule
    scope_names: AstGrepRule
    change_kinds: dict[ChangeKind, AstGrepRule]

    @field_validator("change_kinds")
    @classmethod
    def validate_change_kinds_are_the_syntax_node_kinds(
        cls, change_kinds: dict[ChangeKind, AstGrepRule]
    ) -> dict[ChangeKind, AstGrepRule]:
        expected = {kind for kind in ChangeKind if kind.is_syntax_node}
        missing = sorted(expected - set(change_kinds))
        derived = sorted(set(change_kinds) - expected)
        if missing:
            raise ValueError(f"no rule for change kinds: {', '.join(missing)}")
        if derived:
            raise ValueError(
                f"change kinds computed from the diff can't have a rule: {', '.join(derived)}"
            )
        return change_kinds

    @classmethod
    def for_file(cls, file: str) -> Self | None:
        extension = PurePath(file).suffix.removeprefix(".")
        return next((table for table in cls.supported() if extension in table.extensions), None)

    @classmethod
    @cache
    def supported(cls) -> tuple[Self, ...]:
        return tuple(
            cls.model_validate(yaml.safe_load(file.read_text()))
            for file in sorted(_LANGUAGES_DIR.glob("*.yml"))
        )

    def inline_rules(self, gates: Mapping[str, GateRule]) -> str:
        rules = {
            **{str(kind): getattr(self, kind) for kind in NodeKind},
            **{str(kind): rule for kind, rule in self.change_kinds.items()},
            **{
                gate: rule.rule
                for gate, rule in gates.items()
                if rule.language.lower() == self.language
            },
        }
        return "---\n".join(
            yaml.safe_dump({"id": kind, "language": self.language, "rule": rule})
            for kind, rule in rules.items()
        )
