from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from itertools import groupby
from typing import Self

from codeguard.repository.change_block import ChangeBlock
from codeguard.repository.diff_row import AddedRow, DiffRow, KeptRow, RemovedRow, RowText

_PLAIN_CONTEXT = 3


@dataclass(frozen=True)
class FileDiff:
    base_path: str | None
    added_lines: frozenset[int]
    deletion_points: frozenset[int]
    head_lines_by_base_line: Mapping[int, int]
    removed_base_lines: frozenset[int]
    rows: tuple[DiffRow, ...]

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
            head_lines_by_base_line={
                row.base_line: row.head_line for row in rows if isinstance(row, KeptRow)
            },
            removed_base_lines=frozenset(
                row.base_line for row in rows if isinstance(row, RemovedRow)
            ),
            rows=rows,
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
        return frozenset(
            row.base_line
            for row in self.rows
            if isinstance(row, RemovedRow) and row.text.holds_code
        )

    def kept_head_lines(self, base_lines: Iterable[int]) -> frozenset[int]:
        return frozenset(
            self.head_lines_by_base_line[line]
            for line in base_lines
            if line in self.head_lines_by_base_line
        )

    def unified(self, file: str, head: bytes, context_lines: frozenset[int]) -> str:
        """The unified diff of the file, whose hunks show the kept head lines in
        `context_lines` and the plain context around each changed row."""
        head_rows = head.split(b"\n")
        shown = self._shown_rows(context_lines)
        base = f"a/{self.base_path}" if self.base_path is not None else "/dev/null"
        text = [f"--- {base}\n", f"+++ b/{file}\n"]
        numbered = enumerate(_numbered(self.rows))
        for in_hunk, hunk in groupby(numbered, key=lambda item: item[0] in shown):
            if not in_hunk:
                continue
            entries = [entry for _, entry in hunk]
            base_start, head_start, _ = entries[0]
            rows = [row for _, _, row in entries]
            base_count = sum(not isinstance(row, AddedRow) for row in rows)
            head_count = sum(not isinstance(row, RemovedRow) for row in rows)
            text.append(
                f"@@ -{_hunk_range(base_start, base_count)} "
                f"+{_hunk_range(head_start, head_count)} @@\n"
            )
            text.extend(_diff_line(row, head_rows) for row in rows)
        return "".join(text)

    def _shown_rows(self, context_lines: frozenset[int]) -> set[int]:
        shown: set[int] = set()
        for index, row in enumerate(self.rows):
            if not isinstance(row, KeptRow):
                shown.update(range(index - _PLAIN_CONTEXT, index + _PLAIN_CONTEXT + 1))
            elif row.head_line in context_lines:
                shown.add(index)
        return shown


def _numbered(rows: Iterable[DiffRow]) -> Iterator[tuple[int, int, DiffRow]]:
    base_line = head_line = 1
    for row in rows:
        yield base_line, head_line, row
        base_line += not isinstance(row, AddedRow)
        head_line += not isinstance(row, RemovedRow)


def _hunk_range(start: int, count: int) -> str:
    if count == 0:
        return f"{start - 1},0"
    if count == 1:
        return str(start)
    return f"{start},{count}"


def _diff_line(row: DiffRow, head_rows: list[bytes]) -> str:
    match row:
        case KeptRow():
            mark, text = " ", RowText.of_line(head_rows[row.head_line - 1])
        case AddedRow():
            mark, text = "+", row.text
        case RemovedRow():
            mark, text = "-", row.text
    return f"{mark}{text.content.decode(errors='replace')}\n"
