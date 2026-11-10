from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Self

from codeguard.line_range import LineRange
from codeguard.unified_diff import Hunk, parse
from codeguard.working_tree import WorkingTree

# ASCII whitespace, the same set git treats as blank.
_BLANK = " \t\r\f\v"
# The diff algorithm, rename detection and path quoting are pinned, so a user's git config
# doesn't change which lines count as changed.
_CHANGED_LINES_DIFF = (
    "-c",
    "core.quotePath=false",
    "diff",
    "-U0",
    "--no-color",
    "--no-ext-diff",
    "--no-prefix",
    "--diff-algorithm=myers",
    "--find-renames",
    "--diff-filter=d",
)


@dataclass(frozen=True)
class Removal:
    """Rows a change removed, shown before the new line `before`; a violation in them is
    reported on `line`. `base_lines` are the rows' lines in the base."""

    before: int
    line: int
    rows: tuple[str, ...]
    base_lines: tuple[int, ...]


@dataclass(frozen=True)
class Edit:
    """A hunk: `base_count` rows from line `base_start` of the base replaced by `count` rows
    from line `start`. git numbers an empty side by the line before it."""

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


@dataclass(frozen=True)
class ChangedLines:
    lines: Mapping[str, frozenset[int]]
    deletions: Mapping[str, frozenset[int]] = field(default_factory=dict)
    kinds: Mapping[str, frozenset[str]] = field(default_factory=dict)
    judged: Mapping[str, frozenset[int]] = field(default_factory=dict)
    kind_lines: Mapping[str, Mapping[str, frozenset[int]]] = field(default_factory=dict)
    removals: Mapping[str, tuple[Removal, ...]] = field(default_factory=dict)
    edits: Mapping[str, tuple[Edit, ...]] = field(default_factory=dict)
    sources: Mapping[str, str] = field(default_factory=dict)
    base: str | None = None

    @classmethod
    def of(cls, hunks: Sequence[Hunk], untracked: Mapping[str, frozenset[int]], base: str) -> Self:
        """The lines a diff's hunks change, and every line holding code of each untracked
        file, against `base`."""
        added: dict[str, set[int]] = {}
        deletions: dict[str, set[int]] = {}
        removals: dict[str, list[Removal]] = {}
        edits: dict[str, list[Edit]] = {}
        sources: dict[str, str] = {}
        for hunk in hunks:
            points = _points(hunk)
            removed = _removed_code(hunk)
            added.setdefault(hunk.file, set()).update(points)
            if removed and not points:
                deletions.setdefault(hunk.file, set()).add(_deletion_point(hunk))
            if removed:
                removals.setdefault(hunk.file, []).append(_removal(hunk, points, removed))
            edits.setdefault(hunk.file, []).append(
                Edit(hunk.base_start, hunk.base_count, hunk.start, hunk.count)
            )
            if hunk.base_file not in {hunk.file, ""}:
                sources[hunk.file] = hunk.base_file
        lines = {**_frozen(added), **untracked}
        changed = {file for file, numbers in lines.items() if numbers} | {
            file for file, numbers in deletions.items() if numbers
        }
        return cls(
            lines={file: numbers for file, numbers in lines.items() if numbers},
            deletions={file: numbers for file, numbers in _frozen(deletions).items() if numbers},
            removals={file: tuple(found) for file, found in removals.items()},
            edits={file: tuple(found) for file, found in edits.items() if file in changed},
            sources={file: source for file, source in sources.items() if file in changed},
            base=base,
        )

    @property
    def files(self) -> tuple[str, ...]:
        return tuple(sorted({*self.lines, *self.deletions}))

    def points(self, file: str) -> frozenset[int]:
        return self.lines.get(file, frozenset()) | self.deletions.get(file, frozenset())

    def with_kinds(self, kinds: Mapping[str, frozenset[str]]) -> Self:
        return replace(self, kinds=kinds)

    def with_judged_lines(self, judged: Mapping[str, frozenset[int]]) -> Self:
        return replace(self, judged=judged)

    def with_kind_lines(self, kind_lines: Mapping[str, Mapping[str, frozenset[int]]]) -> Self:
        return replace(self, kind_lines=kind_lines)

    def judged_lines(
        self, file: str, triggers: frozenset[str] = frozenset()
    ) -> frozenset[int] | None:
        spans = self.kind_lines.get(file, {})
        triggered = (spans.get(kind, frozenset()) for kind in triggers)
        return self.judged.get(file, self.points(file)).union(*triggered)

    def added_lines(self, file: str) -> frozenset[int] | None:
        return self.lines.get(file, frozenset())

    def removals_in(self, file: str) -> tuple[Removal, ...]:
        return self.removals.get(file, ())

    def kinds_of(self, file: str) -> frozenset[str] | None:
        return self.kinds.get(file)

    def base_path(self, file: str) -> str | None:
        """The file's path in the base, which a rename changes; None for a file git's diff
        doesn't hold, which is untracked, so new."""
        if file not in self.edits:
            return None
        return self.sources.get(file, file)

    def removed_base_lines(self, file: str) -> frozenset[int]:
        return frozenset(line for edit in self.edits.get(file, ()) for line in edit.base_rows)

    def head_line(self, file: str, base_line: int) -> int | None:
        """The line a base line is in the working tree, or None when the change removed it."""
        line = base_line
        for edit in self.edits.get(file, ()):
            if base_line in edit.base_rows:
                return None
            if base_line > edit.last_base_line:
                line += edit.count - edit.base_count
        return line

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

    def kinds_of(self, file: str) -> frozenset[str] | None:
        return None

    def judged_lines(
        self, file: str, triggers: frozenset[str] = frozenset()
    ) -> frozenset[int] | None:
        return None

    def added_lines(self, file: str) -> frozenset[int] | None:
        return None

    def removals_in(self, file: str) -> tuple[Removal, ...]:
        return ()


@dataclass(frozen=True)
class LineScopes:
    """The changed-line scopes a review checks in a working tree."""

    working_tree: WorkingTree

    def changed_lines(self, base: str) -> ChangedLines:
        merge_base = self.working_tree.merge_base(base)
        diff = self.working_tree.git.text(*_CHANGED_LINES_DIFF, merge_base)
        untracked = {
            file: _code_lines((self.working_tree.root / file).read_bytes())
            for file in self.working_tree.untracked_files()
        }
        return ChangedLines.of(parse(diff), untracked, merge_base)

    def all_lines(self) -> AllLines:
        return AllLines(tuple(sorted(self.working_tree.files())))


def _points(hunk: Hunk) -> set[int]:
    # A blank line changes nothing in any language, so only lines holding code count.
    return {hunk.start + row for row, text in enumerate(hunk.added) if _holds_code(text)}


def _removed_code(hunk: Hunk) -> list[tuple[int, str]]:
    return [
        (hunk.base_start + row, text) for row, text in enumerate(hunk.removed) if _holds_code(text)
    ]


def _deletion_point(hunk: Hunk) -> int:
    return max(hunk.start - 1 if hunk.added else hunk.start, 1)


def _removal(hunk: Hunk, points: set[int], removed: list[tuple[int, str]]) -> Removal:
    # git numbers a hunk that only removes rows by the line before them.
    before = hunk.start if hunk.added else hunk.start + 1
    line = min(points) if points else _deletion_point(hunk)
    return Removal(
        before,
        line,
        # Shown to the judge, so a byte that isn't UTF-8 becomes U+FFFD, as in the file.
        tuple(
            text.removesuffix("\r").encode(errors="surrogateescape").decode(errors="replace")
            for _, text in removed
        ),
        tuple(base_line for base_line, _ in removed),
    )


def _code_lines(content: bytes) -> frozenset[int]:
    rows = content.decode(errors="surrogateescape").split("\n")
    return frozenset(number for number, text in enumerate(rows, 1) if _holds_code(text))


def _holds_code(text: str) -> bool:
    return bool(text.strip(_BLANK))


def _frozen(points: dict[str, set[int]]) -> dict[str, frozenset[int]]:
    return {file: frozenset(numbers) for file, numbers in points.items()}
