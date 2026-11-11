from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Protocol

import pygit2
from pygit2.enums import DeltaStatus

from codeguard.line_range import LineRange
from codeguard.repository.working_tree import WorkingTree

_GIT_BLANK = b" \t\r\f\v"


@dataclass(frozen=True)
class Removal:
    shown_before: int
    reported_line: int
    rows: tuple[str, ...]
    base_lines: tuple[int, ...]


class LineScope(Protocol):
    @property
    def files(self) -> tuple[str, ...]: ...

    def covers(self, file: str, lines: LineRange | None) -> bool: ...

    def added_lines(self, file: str) -> frozenset[int] | None: ...

    def removals_in(self, file: str) -> tuple[Removal, ...]: ...


@dataclass(frozen=True)
class ChangedLines:
    lines: Mapping[str, frozenset[int]]
    deletions: Mapping[str, frozenset[int]] = field(default_factory=dict)
    removals: Mapping[str, tuple[Removal, ...]] = field(default_factory=dict)
    kept: Mapping[str, Mapping[int, int]] = field(default_factory=dict)
    replaced: Mapping[str, frozenset[int]] = field(default_factory=dict)
    base_paths: Mapping[str, str] = field(default_factory=dict)
    base: str | None = None

    @property
    def files(self) -> tuple[str, ...]:
        return tuple(sorted({*self.lines, *self.deletions}))

    def points(self, file: str) -> frozenset[int]:
        return self.lines.get(file, frozenset()) | self.deletions.get(file, frozenset())

    def added_lines(self, file: str) -> frozenset[int] | None:
        return self.lines.get(file, frozenset())

    def removals_in(self, file: str) -> tuple[Removal, ...]:
        return self.removals.get(file, ())

    def base_path(self, file: str) -> str | None:
        return self.base_paths.get(file)

    def removed_code_lines(self, file: str) -> frozenset[int]:
        return frozenset(line for removal in self.removals_in(file) for line in removal.base_lines)

    def replaced_base_rows(self, file: str) -> frozenset[int]:
        return self.replaced.get(file, frozenset())

    def head_lines(self, file: str, base_lines: Iterable[int]) -> frozenset[int]:
        kept = self.kept.get(file, {})
        return frozenset(kept[line] for line in base_lines if line in kept)

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


@dataclass(frozen=True)
class LineScopes:
    working_tree: WorkingTree

    def changed_lines(self, base: str) -> ChangedLines:
        merge_base = self.working_tree.merge_base(base)
        file_diffs = [
            _PatchReader().read(patch) for patch in self.working_tree.patches_since(merge_base)
        ]
        changed = {diff.file: diff for diff in file_diffs if diff.changes_code}
        return ChangedLines(
            lines=_by_file(changed, lambda diff: diff.added),
            deletions=_by_file(changed, lambda diff: diff.deletions),
            removals=_by_file(changed, lambda diff: diff.removals),
            kept=_by_file(changed, lambda diff: diff.kept),
            replaced=_by_file(changed, lambda diff: diff.replaced),
            base_paths=_by_file(changed, lambda diff: diff.base_path),
            base=merge_base,
        )

    def all_lines(self) -> AllLines:
        return AllLines(tuple(sorted(self.working_tree.tracked_and_untracked_files())))


@dataclass(frozen=True)
class _FileDiff:
    file: str
    base_path: str | None
    added: frozenset[int]
    deletions: frozenset[int]
    removals: tuple[Removal, ...]
    kept: Mapping[int, int]
    replaced: frozenset[int]

    @property
    def changes_code(self) -> bool:
        return bool(self.added or self.deletions)


@dataclass
class _PatchReader:
    added: set[int] = field(default_factory=set)
    deletions: set[int] = field(default_factory=set)
    removals: list[Removal] = field(default_factory=list)
    kept: dict[int, int] = field(default_factory=dict)
    replaced: set[int] = field(default_factory=set)
    head_before_run: int = 0
    run_added: list[int] = field(default_factory=list)
    run_removed: list[pygit2.DiffLine] = field(default_factory=list)

    def read(self, patch: pygit2.Patch) -> _FileDiff:
        for hunk in patch.hunks:
            for line in hunk.lines:
                self._read_line(line)
        self._end_run()
        return _FileDiff(
            file=patch.delta.new_file.path,
            base_path=_base_path(patch.delta),
            added=frozenset(self.added),
            deletions=frozenset(self.deletions),
            removals=tuple(self.removals),
            kept=self.kept,
            replaced=frozenset(self.replaced),
        )

    def _read_line(self, line: pygit2.DiffLine) -> None:
        if line.origin == " ":
            self._end_run()
            self.kept[line.old_lineno] = line.new_lineno
            self.head_before_run = line.new_lineno
        elif line.origin == "+" and _holds_code(line.raw_content):
            self.run_added.append(line.new_lineno)
        elif line.origin == "-":
            self.replaced.add(line.old_lineno)
            if _holds_code(line.raw_content):
                self.run_removed.append(line)

    def _end_run(self) -> None:
        line_before = max(self.head_before_run, 1)
        if self.run_removed:
            self.removals.append(
                Removal(
                    shown_before=self.head_before_run + 1,
                    reported_line=min(self.run_added, default=line_before),
                    rows=tuple(_as_shown_to_judge(line.raw_content) for line in self.run_removed),
                    base_lines=tuple(line.old_lineno for line in self.run_removed),
                )
            )
            if not self.run_added:
                self.deletions.add(line_before)
        self.added.update(self.run_added)
        self.run_added = []
        self.run_removed = []


def _base_path(delta: pygit2.DiffDelta) -> str | None:
    if delta.status in {DeltaStatus.ADDED, DeltaStatus.UNTRACKED}:
        return None
    return delta.old_file.path


def _by_file[T](
    file_diffs: Mapping[str, _FileDiff], part: Callable[[_FileDiff], T | None]
) -> dict[str, T]:
    return {file: value for file, diff in file_diffs.items() if (value := part(diff))}


def _as_shown_to_judge(row: bytes) -> str:
    return row.removesuffix(b"\n").removesuffix(b"\r").decode(errors="replace")


def _holds_code(row: bytes) -> bool:
    return bool(row.removesuffix(b"\n").strip(_GIT_BLANK))
