from dataclasses import dataclass, field
from pathlib import Path

import pygit2
from pygit2.enums import DeltaStatus, DiffFind, DiffOption

from codeguard.repository.file_diff import FileDiff, Removal

_GIT_BLANK = b" \t\r\f\v"
_GIT_RENAME_LIMIT = 1000
_WHOLE_FILE_CONTEXT = 2**31 - 1
_TRACKED_DIFF_FLAGS = DiffOption.INDENT_HEURISTIC
_UNTRACKED_DIFF_FLAGS = (
    DiffOption.INCLUDE_UNTRACKED
    | DiffOption.RECURSE_UNTRACKED_DIRS
    | DiffOption.SHOW_UNTRACKED_CONTENT
    | DiffOption.FORCE_TEXT
)


def diff_since(root: Path, merge_base: str) -> dict[str, FileDiff]:
    repository = pygit2.Repository(str(root))
    return {
        patch.delta.new_file.path: _file_diff(patch)
        for patch in [
            *_tracked_patches(repository, merge_base),
            *_untracked_patches(root, repository),
        ]
    }


def _tracked_patches(repository: pygit2.Repository, merge_base: str) -> list[pygit2.Patch]:
    tree = repository.revparse_single(merge_base).peel(pygit2.Tree)
    diff = tree.diff_to_index(repository.index, _TRACKED_DIFF_FLAGS, _WHOLE_FILE_CONTEXT)
    diff.merge(repository.index.diff_to_workdir(_TRACKED_DIFF_FLAGS, _WHOLE_FILE_CONTEXT))
    diff.find_similar(flags=DiffFind.FIND_RENAMES, rename_limit=_GIT_RENAME_LIMIT)
    return [
        patch for patch in diff if patch is not None and patch.delta.status != DeltaStatus.DELETED
    ]


def _untracked_patches(root: Path, repository: pygit2.Repository) -> list[pygit2.Patch]:
    diff = repository.index.diff_to_workdir(_UNTRACKED_DIFF_FLAGS, _WHOLE_FILE_CONTEXT)
    return [
        patch
        for patch in diff
        if patch is not None
        and patch.delta.status == DeltaStatus.UNTRACKED
        and (root / patch.delta.new_file.path).is_file()
    ]


def _file_diff(patch: pygit2.Patch) -> FileDiff:
    builder = _FileDiffBuilder()
    for hunk in patch.hunks:
        for line in hunk.lines:
            builder.add(line)
    return builder.build(_base_path(patch.delta))


@dataclass
class _FileDiffBuilder:
    added_lines: set[int] = field(init=False, default_factory=set)
    deletion_points: set[int] = field(init=False, default_factory=set)
    removals: list[Removal] = field(init=False, default_factory=list)
    kept: dict[int, int] = field(init=False, default_factory=dict)
    replaced_base_rows: set[int] = field(init=False, default_factory=set)
    head_before_run: int = field(init=False, default=0)
    run_added: list[int] = field(init=False, default_factory=list)
    run_removed: list[pygit2.DiffLine] = field(init=False, default_factory=list)

    def add(self, line: pygit2.DiffLine) -> None:
        if line.origin == " ":
            self._end_run()
            self.kept[line.old_lineno] = line.new_lineno
            self.head_before_run = line.new_lineno
        elif line.origin == "+" and _holds_code(line.raw_content):
            self.run_added.append(line.new_lineno)
        elif line.origin == "-":
            self.replaced_base_rows.add(line.old_lineno)
            if _holds_code(line.raw_content):
                self.run_removed.append(line)

    def build(self, base_path: str | None) -> FileDiff:
        self._end_run()
        return FileDiff(
            base_path=base_path,
            added_lines=frozenset(self.added_lines),
            deletion_points=frozenset(self.deletion_points),
            removals=tuple(self.removals),
            kept=dict(self.kept),
            replaced_base_rows=frozenset(self.replaced_base_rows),
        )

    def _end_run(self) -> None:
        line_before = max(self.head_before_run, 1)
        if self.run_removed:
            self.removals.append(
                Removal(
                    shown_before=self.head_before_run + 1,
                    reported_line=min(self.run_added, default=line_before),
                    rows=tuple(_row(line.raw_content) for line in self.run_removed),
                    base_lines=tuple(line.old_lineno for line in self.run_removed),
                )
            )
            if not self.run_added:
                self.deletion_points.add(line_before)
        self.added_lines.update(self.run_added)
        self.run_added = []
        self.run_removed = []


def _base_path(delta: pygit2.DiffDelta) -> str | None:
    if delta.status in {DeltaStatus.ADDED, DeltaStatus.UNTRACKED}:
        return None
    return delta.old_file.path


def _row(raw_content: bytes) -> bytes:
    return raw_content.removesuffix(b"\n").removesuffix(b"\r")


def _holds_code(raw_content: bytes) -> bool:
    return bool(_row(raw_content).strip(_GIT_BLANK))
