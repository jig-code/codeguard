from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Protocol

from codeguard.line_range import LineRange
from codeguard.repository.file_diff import FileDiff, Removal
from codeguard.repository.working_tree import WorkingTree

_UNCHANGED = FileDiff()


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

    def points(self, file: str) -> frozenset[int]:
        return self._diff(file).points

    def added_lines(self, file: str) -> frozenset[int]:
        return self._diff(file).added_lines

    def removals_in(self, file: str) -> tuple[Removal, ...]:
        return self._diff(file).removals

    def base_path(self, file: str) -> str | None:
        return self._diff(file).base_path

    def removed_code_lines(self, file: str) -> frozenset[int]:
        return self._diff(file).removed_code_lines

    def replaced_base_rows(self, file: str) -> frozenset[int]:
        return self._diff(file).replaced_base_rows

    def head_lines(self, file: str, base_lines: Iterable[int]) -> frozenset[int]:
        kept = self._diff(file).kept
        return frozenset(kept[line] for line in base_lines if line in kept)

    def covers(self, file: str, lines: LineRange | None) -> bool:
        if file not in self.diffs:
            return False
        if lines is None:
            return True
        return any(point in lines for point in self.points(file))

    def _diff(self, file: str) -> FileDiff:
        return self.diffs.get(file, _UNCHANGED)


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
            patch.delta.new_file.path: FileDiff.of(patch)
            for patch in self.working_tree.patches_since(merge_base)
        }
        return ChangedLines(
            {file: diff for file, diff in diffs.items() if diff.changes_code}, base=merge_base
        )

    def all_lines(self) -> AllLines:
        return AllLines(tuple(sorted(self.working_tree.tracked_and_untracked_files())))
