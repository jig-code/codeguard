from dataclasses import dataclass
from itertools import groupby
from typing import Self

from codeguard.repository.diff_row import AddedRow, DiffRow, RemovedRow


@dataclass(frozen=True)
class ChangeBlock:
    head_before: int
    added: tuple[AddedRow, ...]
    removed: tuple[RemovedRow, ...]

    @classmethod
    def between_kept_rows(cls, rows: tuple[DiffRow, ...]) -> tuple[Self, ...]:
        blocks: list[Self] = []
        head_before = 0
        for kept_head_line, group in groupby(rows, key=lambda row: row.kept_head_line):
            if kept_head_line is not None:
                head_before = kept_head_line
                continue
            changed = tuple(group)
            blocks.append(
                cls(
                    head_before,
                    added=tuple(row for row in changed if isinstance(row, AddedRow)),
                    removed=tuple(row for row in changed if isinstance(row, RemovedRow)),
                )
            )
        return tuple(blocks)

    @property
    def added_lines(self) -> frozenset[int]:
        return frozenset(row.head_line for row in self.added if row.text.holds_code)

    @property
    def deletion_point(self) -> int | None:
        if self.added_lines or not any(row.text.holds_code for row in self.removed):
            return None
        return max(self.head_before, 1)
