from dataclasses import dataclass, field

import pygit2
from pygit2.enums import DeltaStatus

from codeguard.repository.file_diff import FileDiff, Removal

_GIT_BLANK = b" \t\r\f\v"


def read_patch(patch: pygit2.Patch) -> FileDiff:
    reader = _Reader()
    for hunk in patch.hunks:
        for line in hunk.lines:
            reader.read(line)
    reader.end_run()
    return FileDiff(
        base_path=_base_path(patch.delta),
        added_lines=frozenset(reader.added_lines),
        deletions=frozenset(reader.deletions),
        removals=tuple(reader.removals),
        kept=dict(reader.kept),
        replaced_base_rows=frozenset(reader.replaced_base_rows),
    )


@dataclass
class _Reader:
    added_lines: set[int] = field(init=False, default_factory=set)
    deletions: set[int] = field(init=False, default_factory=set)
    removals: list[Removal] = field(init=False, default_factory=list)
    kept: dict[int, int] = field(init=False, default_factory=dict)
    replaced_base_rows: set[int] = field(init=False, default_factory=set)
    head_before_run: int = field(init=False, default=0)
    run_added: list[int] = field(init=False, default_factory=list)
    run_removed: list[pygit2.DiffLine] = field(init=False, default_factory=list)

    def read(self, line: pygit2.DiffLine) -> None:
        if line.origin == " ":
            self.end_run()
            self.kept[line.old_lineno] = line.new_lineno
            self.head_before_run = line.new_lineno
        elif line.origin == "+" and _holds_code(line.raw_content):
            self.run_added.append(line.new_lineno)
        elif line.origin == "-":
            self.replaced_base_rows.add(line.old_lineno)
            if _holds_code(line.raw_content):
                self.run_removed.append(line)

    def end_run(self) -> None:
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
        self.added_lines.update(self.run_added)
        self.run_added = []
        self.run_removed = []


def _base_path(delta: pygit2.DiffDelta) -> str | None:
    if delta.status in {DeltaStatus.ADDED, DeltaStatus.UNTRACKED}:
        return None
    return delta.old_file.path


def _as_shown_to_judge(row: bytes) -> str:
    return row.removesuffix(b"\n").removesuffix(b"\r").decode(errors="replace")


def _holds_code(row: bytes) -> bool:
    return bool(row.removesuffix(b"\n").strip(_GIT_BLANK))
