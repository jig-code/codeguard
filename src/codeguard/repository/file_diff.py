from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from itertools import groupby
from typing import Self

from codeguard.repository.change_block import ChangeBlock
from codeguard.repository.diff_row import AddedRow, DiffRow, KeptRow, RemovedRow, RowText

_PLAIN_CONTEXT = 3
# git calls a file binary when a NUL byte falls in its first 8000 bytes.
_BINARY_SNIFF_BYTES = 8000


@dataclass(frozen=True)
class FileDiff:
    base_path: str | None
    added_lines: frozenset[int]
    deletion_points: frozenset[int]
    head_lines_by_base_line: Mapping[int, int]
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
            rows=rows,
        )

    @classmethod
    def from_new_file(cls, content: bytes) -> Self:
        return cls.from_whole_file_rows(
            None,
            (AddedRow(number, text) for number, text in enumerate(RowText.lines_of(content), 1)),
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
        base = f"a/{self.base_path}" if self.base_path is not None else "/dev/null"
        if b"\0" in head[:_BINARY_SNIFF_BYTES]:
            return f"Binary files {base} and b/{file} differ\n"
        head_texts = RowText.lines_of(head)
        shown = self._shown_rows(context_lines)
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
            text.extend(_diff_line(row, head_texts) for row in rows)
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


def _diff_line(row: DiffRow, head_texts: list[RowText]) -> str:
    match row:
        case KeptRow():
            mark, text = " ", head_texts[row.head_line - 1]
        case AddedRow():
            mark, text = "+", row.text
        case RemovedRow():
            mark, text = "-", row.text
    line = f"{mark}{text.content.decode(errors='replace')}\n"
    return line if text.ends_with_newline else f"{line}\\ No newline at end of file\n"
