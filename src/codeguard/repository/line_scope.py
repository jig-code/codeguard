import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Protocol, Self

from codeguard.line_range import LineRange
from codeguard.repository.working_tree import WorkingTree

_HUNK = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_GIT_BLANK = " \t\r\f\v"


@dataclass(frozen=True)
class Removal:
    shown_before: int
    reported_line: int
    rows: tuple[str, ...]
    base_lines: tuple[int, ...]


@dataclass(frozen=True)
class Edit:
    """git numbers an empty side by the line before it."""

    base_start: int
    base_count: int
    start: int
    count: int

    @property
    def base_rows(self) -> range:
        return range(self.base_start, self.base_start + self.base_count)

    @property
    def last_base_line(self) -> int:
        return self.base_start + self.base_count - 1 if self.base_count else self.base_start


class LineScope(Protocol):
    @property
    def files(self) -> tuple[str, ...]: ...

    def covers(self, file: str, lines: LineRange | None) -> bool: ...

    def added_lines(self, file: str) -> frozenset[int] | None: ...

    def removals_in(self, file: str) -> tuple[Removal, ...]: ...

    def classified[T](self, classify: Callable[["ChangedLines"], T], unclassified: T) -> T: ...


@dataclass(frozen=True)
class ChangedLines:
    lines: Mapping[str, frozenset[int]]
    deletions: Mapping[str, frozenset[int]] = field(default_factory=dict)
    removals: Mapping[str, tuple[Removal, ...]] = field(default_factory=dict)
    edits: Mapping[str, tuple[Edit, ...]] = field(default_factory=dict)
    sources: Mapping[str, str] = field(default_factory=dict)
    base: str | None = None

    @property
    def files(self) -> tuple[str, ...]:
        return tuple(sorted({*self.lines, *self.deletions}))

    def points(self, file: str) -> frozenset[int]:
        return self.lines.get(file, frozenset()) | self.deletions.get(file, frozenset())

    def with_edits(self, edits: Mapping[str, tuple[Edit, ...]]) -> Self:
        return replace(self, edits=edits)

    def with_sources(self, sources: Mapping[str, str]) -> Self:
        return replace(self, sources=sources)

    def added_lines(self, file: str) -> frozenset[int] | None:
        return self.lines.get(file, frozenset())

    def removals_in(self, file: str) -> tuple[Removal, ...]:
        return self.removals.get(file, ())

    def classified[T](self, classify: Callable[["ChangedLines"], T], unclassified: T) -> T:
        return classify(self)

    def base_path(self, file: str) -> str | None:
        if self._is_untracked(file):
            return None
        return self.sources.get(file, file)

    def removed_code_lines(self, file: str) -> frozenset[int]:
        return frozenset(line for removal in self.removals_in(file) for line in removal.base_lines)

    def replaced_base_rows(self, file: str) -> frozenset[int]:
        return frozenset(line for edit in self.edits.get(file, ()) for line in edit.base_rows)

    def head_line(self, file: str, base_line: int) -> int | None:
        line = base_line
        for edit in self.edits.get(file, ()):
            if base_line in edit.base_rows:
                return None
            if base_line > edit.last_base_line:
                line += edit.count - edit.base_count
        return line

    def _is_untracked(self, file: str) -> bool:
        return file not in self.edits

    def covers(self, file: str, lines: LineRange | None) -> bool:
        if file not in self.files:
            return False
        if lines is None:
            return True
        return any(point in lines for point in self.points(file))


@dataclass(frozen=True)
class AllLines:
    files: tuple[str, ...]

    def covers(self, file: str, lines: LineRange | None) -> bool:
        return True

    def added_lines(self, file: str) -> frozenset[int] | None:
        return None

    def removals_in(self, file: str) -> tuple[Removal, ...]:
        return ()

    def classified[T](self, classify: Callable[[ChangedLines], T], unclassified: T) -> T:
        return unclassified


@dataclass(frozen=True)
class LineScopes:
    working_tree: WorkingTree

    def changed_lines(self, base: str) -> ChangedLines:
        merge_base = self.working_tree.merge_base(base)
        # Decoded without newline translation, so only "\n" ends a row, as it does for git.
        diff = self.working_tree.git.bytes(
            "-c",
            "core.quotePath=false",
            "diff",
            "-U0",
            "--no-color",
            "--no-ext-diff",
            "--no-prefix",
            "--diff-filter=d",
            merge_base,
        ).decode(errors="surrogateescape")
        untracked = self.working_tree.untracked_files()
        hunks = _hunks(diff)
        added, deletions = _changed_points(hunks)
        lines = {**added, **{file: self._code_lines(file) for file in untracked}}
        changed = ChangedLines(
            lines={file: numbers for file, numbers in lines.items() if numbers},
            deletions={file: numbers for file, numbers in deletions.items() if numbers},
            removals=_removals(hunks),
            base=merge_base,
        )
        edits = _edits(hunks)
        sources = _sources(hunks)
        return changed.with_edits(
            {file: edits[file] for file in changed.files if file in edits}
        ).with_sources({file: sources[file] for file in changed.files if file in sources})

    def all_lines(self) -> AllLines:
        return AllLines(tuple(sorted(self.working_tree.tracked_and_untracked_files())))

    def _code_lines(self, file: str) -> frozenset[int]:
        lines = _rows((self.working_tree.root / file).read_bytes())
        return frozenset(number for number, text in enumerate(lines, 1) if _holds_code(text))


def _changed_points(
    hunks: Sequence["_Hunk"],
) -> tuple[dict[str, frozenset[int]], dict[str, frozenset[int]]]:
    added: dict[str, set[int]] = {}
    deletions: dict[str, set[int]] = {}
    for hunk in hunks:
        added.setdefault(hunk.file, set()).update(hunk.points)
        deletions.setdefault(hunk.file, set())
        if not hunk.points and hunk.removed:
            deletions[hunk.file].add(hunk.deletion_point)
    return _frozen(added), _frozen(deletions)


def _removals(hunks: Sequence["_Hunk"]) -> dict[str, tuple[Removal, ...]]:
    removals: dict[str, list[Removal]] = {}
    for hunk in hunks:
        if hunk.removed:
            removals.setdefault(hunk.file, []).append(hunk.removal)
    return {file: tuple(found) for file, found in removals.items()}


def _sources(hunks: Sequence["_Hunk"]) -> dict[str, str]:
    return {hunk.file: hunk.base_file for hunk in hunks if hunk.base_file not in {hunk.file, ""}}


def _edits(hunks: Sequence["_Hunk"]) -> dict[str, tuple[Edit, ...]]:
    edits: dict[str, list[Edit]] = {}
    for hunk in hunks:
        edits.setdefault(hunk.file, []).append(hunk.edit)
    return {file: tuple(found) for file, found in edits.items()}


@dataclass
class _Hunk:
    file: str
    base_file: str
    base_start: int
    base_count: int
    start: int
    count: int
    points: set[int] = field(default_factory=set)
    added_rows: int = 0
    removed_rows: int = 0
    removed: list[str] = field(default_factory=list)
    removed_lines: list[int] = field(default_factory=list)

    @property
    def edit(self) -> Edit:
        return Edit(self.base_start, self.base_count, self.start, self.count)

    @property
    def deletion_point(self) -> int:
        return max(self.start - 1 if self.added_rows else self.start, 1)

    @property
    def removal(self) -> Removal:
        # git numbers a hunk that only removes rows by the line before them.
        shown_before = self.start if self.added_rows else self.start + 1
        reported_line = min(self.points) if self.points else self.deletion_point
        return Removal(shown_before, reported_line, tuple(self.removed), tuple(self.removed_lines))

    def add(self, text: str) -> None:
        if _holds_code(text):
            self.points.add(self.start + self.added_rows)
        self.added_rows += 1

    def remove(self, text: str) -> None:
        if _holds_code(text):
            self.removed.append(_as_shown_to_judge(text))
            self.removed_lines.append(self.base_start + self.removed_rows)
        self.removed_rows += 1


def _hunks(diff: str) -> list[_Hunk]:
    hunks: list[_Hunk] = []
    file = ""
    base_file = ""
    in_header = False
    for row in _rows(diff):
        if row.startswith("diff --git "):
            in_header = True
        elif in_header and row.startswith("--- "):
            # git ends the name with a tab when it holds a space.
            name = row.removeprefix("--- ").removesuffix("\t")
            base_file = "" if name == "/dev/null" else name
        elif in_header and row.startswith("+++ "):
            file = row.removeprefix("+++ ").removesuffix("\t")
        elif match := _HUNK.match(row):
            in_header = False
            base_start, base_count, start, count = match.groups()
            hunks.append(
                _Hunk(
                    file,
                    base_file,
                    int(base_start),
                    _count(base_count),
                    int(start),
                    _count(count),
                )
            )
        elif not in_header and hunks and row.startswith("-"):
            hunks[-1].remove(row[1:])
        elif not in_header and hunks and row.startswith("+"):
            hunks[-1].add(row[1:])
    return hunks


def _count(group: str | None) -> int:
    # git leaves out a count of 1.
    return 1 if group is None else int(group)


def _rows(text: str | bytes) -> list[str]:
    decoded = text if isinstance(text, str) else text.decode(errors="surrogateescape")
    return decoded.split("\n")


def _as_shown_to_judge(text: str) -> str:
    row = text.removesuffix("\r").encode(errors="surrogateescape")
    return row.decode(errors="replace")


def _holds_code(text: str) -> bool:
    return bool(text.strip(_GIT_BLANK))


def _frozen(points: dict[str, set[int]]) -> dict[str, frozenset[int]]:
    return {file: frozenset(numbers) for file, numbers in points.items()}
