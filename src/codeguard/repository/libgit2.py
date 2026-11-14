from dataclasses import dataclass
from pathlib import Path

import pygit2
from pygit2.enums import DeltaStatus, DiffFind, DiffOption

from codeguard.repository.diff_row import AddedRow, DiffRow, KeptRow, RemovedRow, RowText
from codeguard.repository.file_diff import FileDiff

_WHOLE_FILE_CONTEXT = 2**31 - 1
_TRACKED_DIFF_FLAGS = DiffOption.INDENT_HEURISTIC
_NO_NEWLINE_MARKERS = frozenset({"=", ">", "<"})


@dataclass(frozen=True)
class Libgit2:
    root: Path

    def tracked_diffs(self, merge_base: str) -> dict[str, FileDiff]:
        repository = pygit2.Repository(str(self.root))
        tree = repository.revparse_single(merge_base).peel(pygit2.Tree)
        diff = tree.diff_to_index(repository.index, _TRACKED_DIFF_FLAGS, _WHOLE_FILE_CONTEXT)
        diff.merge(repository.index.diff_to_workdir(_TRACKED_DIFF_FLAGS, _WHOLE_FILE_CONTEXT))
        diff.find_similar(flags=DiffFind.FIND_RENAMES)
        return {
            patch.delta.new_file.path: FileDiff.from_whole_file_rows(
                _base_path(patch.delta), _rows(patch)
            )
            for patch in diff
            if patch is not None and patch.delta.status != DeltaStatus.DELETED
        }


def _rows(patch: pygit2.Patch) -> list[DiffRow]:
    return [
        _row(line)
        for hunk in patch.hunks
        for line in hunk.lines
        if line.origin not in _NO_NEWLINE_MARKERS
    ]


def _row(line: pygit2.DiffLine) -> DiffRow:
    match line.origin:
        case " ":
            return KeptRow(line.old_lineno, line.new_lineno)
        case "+":
            return AddedRow(line.new_lineno, RowText.of_line(line.raw_content))
        case "-":
            return RemovedRow(line.old_lineno, RowText.of_line(line.raw_content))
        case origin:
            raise ValueError(f"libgit2 gave a diff line with origin {origin!r}")


def _base_path(delta: pygit2.DiffDelta) -> str | None:
    if delta.status == DeltaStatus.ADDED:
        return None
    return delta.old_file.path
