from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from codeguard.line_range import LineRange
from codeguard.repository.file_diff import FileDiff, Removal
from codeguard.repository.libgit2 import Libgit2
from codeguard.repository.working_tree import WorkingTree


class LineScope(Protocol):
    @property
    def files(self) -> tuple[str, ...]: ...

    def covers(self, file: str, lines: LineRange | None) -> bool: ...

    def added_lines(self, file: str) -> frozenset[int] | None: ...

    def removals_in(self, file: str) -> tuple[Removal, ...]: ...


@dataclass(frozen=True)
class ChangedLines:
    diffs: Mapping[str, FileDiff] = field(default_factory=dict)
    base: str | None = None

    @property
    def files(self) -> tuple[str, ...]:
        return tuple(sorted(self.diffs))

    def added_lines(self, file: str) -> frozenset[int]:
        return self.diffs[file].added_lines

    def removals_in(self, file: str) -> tuple[Removal, ...]:
        return self.diffs[file].removals

    def covers(self, file: str, lines: LineRange | None) -> bool:
        if file not in self.diffs:
            return False
        if lines is None:
            return True
        return any(point in lines for point in self.diffs[file].points)


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
        diffs = {
            **Libgit2(self.working_tree.root).tracked_diffs(merge_base),
            **{
                file: FileDiff.of_new_file(self.working_tree.contents(file))
                for file in self.working_tree.untracked_files()
            },
        }
        return ChangedLines(
            {file: diff for file, diff in diffs.items() if diff.changes_code}, base=merge_base
        )

    def all_lines(self) -> AllLines:
        return AllLines(tuple(sorted(self.working_tree.tracked_and_untracked_files())))
