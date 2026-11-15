from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Self

from codeguard.config import ChangeKind
from codeguard.repository import FileDiff
from codeguard.syntax.parsed_file import ParsedFile


@dataclass(frozen=True)
class FileClassification:
    touched_kinds: frozenset[str] | None
    context_lines: frozenset[int]

    @classmethod
    def of_change(
        cls, diff: FileDiff, parsed: ParsedFile | None, before: ParsedFile | None
    ) -> Self:
        if parsed is None:
            return cls(touched_kinds=None, context_lines=frozenset())
        added = diff.added_lines
        removed_code = diff.removed_code_lines
        context_lines = parsed.scope_lines(added)
        if before is not None:
            context_lines |= diff.kept_head_lines(before.scope_lines(removed_code))
        return cls(parsed.touched_kinds(added, before, removed_code), context_lines)


@dataclass(frozen=True)
class Classification:
    files: Mapping[str, FileClassification] = field(default_factory=dict)

    def touched_kinds(self, file: str) -> frozenset[str] | None:
        classified = self.files.get(file)
        return None if classified is None else classified.touched_kinds

    def is_triggered(self, file: str, triggers: frozenset[str]) -> bool:
        kinds = self.touched_kinds(file)
        return kinds is None or ChangeKind.ANY in triggers or not triggers.isdisjoint(kinds)

    def context_lines(self, file: str) -> frozenset[int]:
        classified = self.files.get(file)
        return frozenset() if classified is None else classified.context_lines
