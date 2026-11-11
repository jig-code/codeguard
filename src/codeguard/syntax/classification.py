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
    kind_lines: Mapping[str, frozenset[int]] = field(default_factory=dict)

    @classmethod
    def of_change(cls, diff: FileDiff, parsed: ParsedFile, before: ParsedFile | None) -> Self:
        added = diff.added_lines
        removed_code = diff.removed_code_lines
        context_lines = parsed.judged_lines(added)
        kind_lines = parsed.kind_lines(added)
        if before is not None:
            removed = diff.removed_base_lines
            context_lines |= diff.kept_head_lines(
                before.judged_lines(removed_code, replaced=removed)
            )
            for kind, lines in before.kind_lines(removed_code, replaced=removed).items():
                kind_lines[kind] = kind_lines.get(kind, frozenset()) | diff.kept_head_lines(lines)
        return cls(parsed.touched_kinds(added, before, removed_code), context_lines, kind_lines)

    def judged_lines(self, triggers: frozenset[str]) -> frozenset[int]:
        return self.context_lines.union(
            *(self.kind_lines.get(kind, frozenset()) for kind in triggers)
        )


@dataclass(frozen=True)
class Classification:
    files: Mapping[str, FileClassification] = field(default_factory=dict)

    def touched_kinds(self, file: str) -> frozenset[str] | None:
        classified = self.files.get(file)
        return None if classified is None else classified.touched_kinds

    def is_triggered(self, file: str, triggers: frozenset[str]) -> bool:
        kinds = self.touched_kinds(file)
        return kinds is None or ChangeKind.ANY in triggers or not triggers.isdisjoint(kinds)

    def judged_lines(self, file: str, triggers: frozenset[str]) -> frozenset[int] | None:
        classified = self.files.get(file)
        return None if classified is None else classified.judged_lines(triggers)
