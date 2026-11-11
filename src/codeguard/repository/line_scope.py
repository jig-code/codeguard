from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Protocol

from codeguard.line_range import LineRange
from codeguard.repository.patch_reader import FileDiff, PatchReader
from codeguard.repository.removal import Removal
from codeguard.repository.working_tree import WorkingTree


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
            PatchReader().read(patch) for patch in self.working_tree.patches_since(merge_base)
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


def _by_file[T](
    file_diffs: Mapping[str, FileDiff], part: Callable[[FileDiff], T | None]
) -> dict[str, T]:
    return {file: value for file, diff in file_diffs.items() if (value := part(diff))}
