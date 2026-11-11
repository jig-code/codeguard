from collections.abc import Mapping
from dataclasses import dataclass, field

from codeguard.config import ChangeKind


@dataclass(frozen=True)
class FileClassification:
    touched_kinds: frozenset[str] | None
    context_lines: frozenset[int]
    kind_lines: Mapping[str, frozenset[int]] = field(default_factory=dict)

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
