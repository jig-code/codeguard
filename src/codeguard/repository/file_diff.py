from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Self

from codeguard.repository.change_block import ChangeBlock, Removal
from codeguard.repository.diff_row import AddedRow, DiffRow, KeptRow, RemovedRow, RowText


@dataclass(frozen=True)
class FileDiff:
    base_path: str | None
    added_lines: frozenset[int]
    deletion_points: frozenset[int]
    removals: tuple[Removal, ...]
    head_lines_by_base_line: Mapping[int, int]
    removed_base_lines: frozenset[int]

    @classmethod
    def from_whole_file_rows(cls, base_path: str | None, rows: Iterable[DiffRow]) -> Self:
        rows = tuple(rows)
        blocks = ChangeBlock.between_kept_rows(rows)
        return cls(
            base_path=base_path,
            added_lines=frozenset(line for block in blocks for line in block.added_lines),
            deletion_points=frozenset(
                point for block in blocks if (point := block.deletion_point) is not None
            ),
            removals=tuple(removal for block in blocks if (removal := block.removal) is not None),
            head_lines_by_base_line={
                row.base_line: row.head_line for row in rows if isinstance(row, KeptRow)
            },
            removed_base_lines=frozenset(
                row.base_line for row in rows if isinstance(row, RemovedRow)
            ),
        )

    @classmethod
    def from_new_file(cls, content: bytes) -> Self:
        lines = content.split(b"\n")
        if lines[-1] == b"":
            lines.pop()
        return cls.from_whole_file_rows(
            None, (AddedRow(number, RowText.of_line(line)) for number, line in enumerate(lines, 1))
        )

    @property
    def changes_code(self) -> bool:
        return bool(self.added_lines or self.deletion_points)

    @property
    def points(self) -> frozenset[int]:
        return self.added_lines | self.deletion_points

    @property
    def removed_code_lines(self) -> frozenset[int]:
        return frozenset(row.base_line for removal in self.removals for row in removal.rows)

    def kept_head_lines(self, base_lines: Iterable[int]) -> frozenset[int]:
        return frozenset(
            self.head_lines_by_base_line[line]
            for line in base_lines
            if line in self.head_lines_by_base_line
        )
