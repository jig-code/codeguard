from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from itertools import groupby
from typing import Self

_GIT_BLANK = b" \t\r\f\v"


@dataclass(frozen=True)
class KeptRow:
    base_line: int
    head_line: int


@dataclass(frozen=True, kw_only=True)
class _TextRow:
    text: bytes

    @property
    def holds_code(self) -> bool:
        return bool(self.text.strip(_GIT_BLANK))

    @staticmethod
    def _without_line_ending(content: bytes) -> bytes:
        return content.removesuffix(b"\n").removesuffix(b"\r")


@dataclass(frozen=True)
class AddedRow(_TextRow):
    head_line: int

    @classmethod
    def of_content(cls, head_line: int, content: bytes) -> Self:
        return cls(head_line, text=cls._without_line_ending(content))


@dataclass(frozen=True)
class RemovedRow(_TextRow):
    base_line: int

    @classmethod
    def of_content(cls, base_line: int, content: bytes) -> Self:
        return cls(base_line, text=cls._without_line_ending(content))


type DiffRow = KeptRow | AddedRow | RemovedRow


@dataclass(frozen=True)
class Removal:
    shown_before: int
    reported_line: int
    rows: tuple[RemovedRow, ...]


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
        runs = _ChangeRun.split(rows)
        return cls(
            base_path=base_path,
            added_lines=frozenset(line for run in runs for line in run.added_lines),
            deletion_points=frozenset(
                point for run in runs if (point := run.deletion_point) is not None
            ),
            removals=tuple(removal for run in runs if (removal := run.removal) is not None),
            head_lines_by_base_line={
                row.base_line: row.head_line for row in rows if isinstance(row, KeptRow)
            },
            removed_base_lines=frozenset(
                row.base_line for row in rows if isinstance(row, RemovedRow)
            ),
        )

    @classmethod
    def of_new_file(cls, content: bytes) -> Self:
        lines = content.split(b"\n")
        if lines[-1] == b"":
            lines.pop()
        return cls.from_whole_file_rows(
            None, (AddedRow.of_content(number, text) for number, text in enumerate(lines, 1))
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
            if line not in self.removed_base_lines
        )


@dataclass(frozen=True)
class _ChangeRun:
    head_before: int
    added: tuple[AddedRow, ...]
    removed: tuple[RemovedRow, ...]

    @classmethod
    def split(cls, rows: tuple[DiffRow, ...]) -> tuple[Self, ...]:
        runs: list[Self] = []
        head_before = 0
        for kept, group in groupby(rows, key=lambda row: isinstance(row, KeptRow)):
            changed = tuple(group)
            if kept:
                head_before = max(row.head_line for row in changed if isinstance(row, KeptRow))
                continue
            runs.append(
                cls(
                    head_before,
                    added=tuple(row for row in changed if isinstance(row, AddedRow)),
                    removed=tuple(row for row in changed if isinstance(row, RemovedRow)),
                )
            )
        return tuple(runs)

    @property
    def added_lines(self) -> frozenset[int]:
        return frozenset(row.head_line for row in self.added if row.holds_code)

    @property
    def removal(self) -> Removal | None:
        removed_code = tuple(row for row in self.removed if row.holds_code)
        if not removed_code:
            return None
        return Removal(
            shown_before=self.head_before + 1,
            reported_line=min(self.added_lines, default=self._line_before),
            rows=removed_code,
        )

    @property
    def deletion_point(self) -> int | None:
        if self.added_lines or self.removal is None:
            return None
        return self._line_before

    @property
    def _line_before(self) -> int:
        return max(self.head_before, 1)
