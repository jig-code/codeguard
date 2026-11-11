from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Removal:
    shown_before: int
    reported_line: int
    rows: tuple[bytes, ...]
    base_lines: tuple[int, ...]


@dataclass(frozen=True)
class FileDiff:
    base_path: str | None = None
    added_lines: frozenset[int] = frozenset()
    deletion_points: frozenset[int] = frozenset()
    removals: tuple[Removal, ...] = ()
    kept: Mapping[int, int] = field(default_factory=dict)
    replaced_base_rows: frozenset[int] = frozenset()

    @property
    def changes_code(self) -> bool:
        return bool(self.added_lines or self.deletion_points)

    @property
    def points(self) -> frozenset[int]:
        return self.added_lines | self.deletion_points

    @property
    def removed_code_lines(self) -> frozenset[int]:
        return frozenset(line for removal in self.removals for line in removal.base_lines)

    def kept_head_lines(self, base_lines: Iterable[int]) -> frozenset[int]:
        return frozenset(self.kept[line] for line in base_lines if line in self.kept)
