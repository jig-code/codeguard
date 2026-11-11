from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Protocol, Self

import pygit2
from pygit2.enums import DeltaStatus, DiffFind, DiffOption

from codeguard.line_range import LineRange
from codeguard.repository.working_tree import WorkingTree

_GIT_BLANK = b" \t\r\f\v"
_GIT_RENAME_LIMIT = 1000
_WHOLE_FILE_CONTEXT = 2**31 - 1
_TRACKED = DiffOption.INDENT_HEURISTIC
_UNTRACKED = (
    DiffOption.INCLUDE_UNTRACKED
    | DiffOption.RECURSE_UNTRACKED_DIRS
    | DiffOption.SHOW_UNTRACKED_CONTENT
    | DiffOption.FORCE_TEXT
)


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
        repository = pygit2.Repository(str(self.working_tree.root))
        files = {
            **{
                patch.delta.new_file.path: _FileChange.of(patch, base_path=_base_path(patch))
                for patch in self._tracked_patches(repository, merge_base)
            },
            **{
                patch.delta.new_file.path: _FileChange.of(patch, base_path=None)
                for patch in self._untracked_patches(repository)
            },
        }
        changed = {file: change for file, change in files.items() if change.changes_code}
        return ChangedLines(
            lines={
                file: frozenset(change.added) for file, change in changed.items() if change.added
            },
            deletions={
                file: frozenset(change.deletions)
                for file, change in changed.items()
                if change.deletions
            },
            removals={
                file: tuple(change.removals) for file, change in changed.items() if change.removals
            },
            kept={file: change.kept for file, change in changed.items() if change.kept},
            replaced={
                file: frozenset(change.replaced)
                for file, change in changed.items()
                if change.replaced
            },
            base_paths={
                file: change.base_path
                for file, change in changed.items()
                if change.base_path is not None
            },
            base=merge_base,
        )

    def all_lines(self) -> AllLines:
        return AllLines(tuple(sorted(self.working_tree.tracked_and_untracked_files())))

    def _tracked_patches(
        self, repository: pygit2.Repository, merge_base: str
    ) -> list[pygit2.Patch]:
        tree = repository.revparse_single(merge_base).peel(pygit2.Tree)
        diff = tree.diff_to_index(
            repository.index, flags=_TRACKED, context_lines=_WHOLE_FILE_CONTEXT
        )
        diff.merge(
            repository.index.diff_to_workdir(flags=_TRACKED, context_lines=_WHOLE_FILE_CONTEXT)
        )
        diff.find_similar(flags=DiffFind.FIND_RENAMES, rename_limit=_GIT_RENAME_LIMIT)
        return [
            patch
            for patch in diff
            if patch is not None and patch.delta.status != DeltaStatus.DELETED
        ]

    def _untracked_patches(self, repository: pygit2.Repository) -> list[pygit2.Patch]:
        diff = repository.index.diff_to_workdir(flags=_UNTRACKED, context_lines=_WHOLE_FILE_CONTEXT)
        return [
            patch
            for patch in diff
            if patch is not None
            and patch.delta.status == DeltaStatus.UNTRACKED
            and (self.working_tree.root / patch.delta.new_file.path).is_file()
        ]


@dataclass
class _FileChange:
    base_path: str | None
    added: set[int] = field(default_factory=set)
    deletions: set[int] = field(default_factory=set)
    removals: list[Removal] = field(default_factory=list)
    kept: dict[int, int] = field(default_factory=dict)
    replaced: set[int] = field(default_factory=set)
    _head_before_run: int = 0
    _run_added: list[int] = field(default_factory=list)
    _run_removed: list[pygit2.DiffLine] = field(default_factory=list)

    @classmethod
    def of(cls, patch: pygit2.Patch, base_path: str | None) -> Self:
        change = cls(base_path)
        for hunk in patch.hunks:
            for line in hunk.lines:
                change._read(line)
        change._end_run()
        return change

    @property
    def changes_code(self) -> bool:
        return bool(self.added or self.deletions)

    def _read(self, line: pygit2.DiffLine) -> None:
        if line.origin == " ":
            self._end_run()
            self.kept[line.old_lineno] = line.new_lineno
            self._head_before_run = line.new_lineno
        elif line.origin == "+" and _holds_code(line.raw_content):
            self._run_added.append(line.new_lineno)
        elif line.origin == "-":
            self.replaced.add(line.old_lineno)
            if _holds_code(line.raw_content):
                self._run_removed.append(line)

    def _end_run(self) -> None:
        line_before = max(self._head_before_run, 1)
        if self._run_removed:
            self.removals.append(
                Removal(
                    shown_before=self._head_before_run + 1,
                    reported_line=min(self._run_added, default=line_before),
                    rows=tuple(_as_shown_to_judge(line.raw_content) for line in self._run_removed),
                    base_lines=tuple(line.old_lineno for line in self._run_removed),
                )
            )
            if not self._run_added:
                self.deletions.add(line_before)
        self.added.update(self._run_added)
        self._run_added = []
        self._run_removed = []


def _base_path(patch: pygit2.Patch) -> str | None:
    if patch.delta.status == DeltaStatus.ADDED:
        return None
    return patch.delta.old_file.path


def _as_shown_to_judge(row: bytes) -> str:
    return row.removesuffix(b"\n").removesuffix(b"\r").decode(errors="replace")


def _holds_code(row: bytes) -> bool:
    return bool(row.removesuffix(b"\n").strip(_GIT_BLANK))
