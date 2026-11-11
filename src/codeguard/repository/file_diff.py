from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Removal:
    shown_before: int
    reported_line: int
    rows: tuple[str, ...]
    base_lines: tuple[int, ...]


@dataclass(frozen=True)
class FileDiff:
    base_path: str | None = None
    added_lines: frozenset[int] = frozenset()
    deletions: frozenset[int] = frozenset()
    removals: tuple[Removal, ...] = ()
    kept: Mapping[int, int] = field(default_factory=dict)
    replaced_base_rows: frozenset[int] = frozenset()

    @property
    def changes_code(self) -> bool:
        return bool(self.added_lines or self.deletions)

    @property
    def points(self) -> frozenset[int]:
        return self.added_lines | self.deletions

    @property
    def removed_code_lines(self) -> frozenset[int]:
        return frozenset(line for removal in self.removals for line in removal.base_lines)
