import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Self

_HUNK = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
# ASCII whitespace, the same set git treats as blank.
_BLANK = " \t\r\f\v"


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

    @property
    def files(self) -> tuple[str, ...]:
        return tuple(sorted({*self.lines, *self.deletions}))

    def points(self, file: str) -> frozenset[int]:
        return self.lines.get(file, frozenset()) | self.deletions.get(file, frozenset())

    def with_edits(self, edits: Mapping[str, tuple[Edit, ...]]) -> Self:
        return replace(self, edits=edits)

    def with_sources(self, sources: Mapping[str, str]) -> Self:
        return replace(self, sources=sources)

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

    def covers(self, file: str, line: int | None, end_line: int | None = None) -> bool:
        if file not in self.files:
            return False
        if line is None:
            return True
        if end_line is not None:
            return any(line <= point <= end_line for point in self.points(file))
        return line in self.points(file)


@dataclass(frozen=True)
class AllLines:
    files: tuple[str, ...]

    def covers(self, file: str, line: int | None, end_line: int | None = None) -> bool:
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
class WorkingTree:
    root: Path

    @classmethod
    def containing(cls, path: Path) -> Self:
        return cls(Path(_run_git(path, "rev-parse", "--show-toplevel").strip()))

    def changed_lines(self, base: str) -> ChangedLines:
        merge_base = self._git("merge-base", base, "HEAD").strip()
        diff = self._git_text(
            "-c",
            "core.quotePath=false",
            "diff",
            "-U0",
            "--no-color",
            "--no-ext-diff",
            "--no-prefix",
            "--diff-filter=d",
            merge_base,
        )
        untracked = {
            file
            for file in self._git_paths("ls-files", "--others", "--exclude-standard")
            if (self.root / file).is_file()
        }
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

    def base_contents(self, base: str, files: Sequence[str]) -> dict[str, bytes]:
        if not files:
            return {}
        in_base = self._git_paths("ls-tree", "-r", "--name-only", base, "--", *files)
        return {
            file: self._git_bytes("show", f"{base}:{file}") for file in files if file in in_base
        }

    def all_lines(self) -> AllLines:
        listed = self._git_paths("ls-files", "--cached", "--others", "--exclude-standard")
        return AllLines(tuple(sorted(path for path in listed if (self.root / path).is_file())))

    def git_path(self, name: str) -> Path:
        return self.root / self._git("rev-parse", "--git-path", name).strip()

    def _code_lines(self, file: str) -> frozenset[int]:
        lines = _rows((self.root / file).read_bytes())
        return frozenset(number for number, text in enumerate(lines, 1) if _holds_code(text))

    def _git_paths(self, command: str, *args: str) -> set[str]:
        return set(self._git(command, "-z", *args).split("\0")) - {""}

    def _git(self, *args: str) -> str:
        return _run_git(self.root, *args)

    def _git_text(self, *args: str) -> str:
        # Decoded without newline translation, so only "\n" ends a row, as it does for git.
        return self._git_bytes(*args).decode(errors="surrogateescape")

    def _git_bytes(self, *args: str) -> bytes:
        return subprocess.run(
            ["git", *args], cwd=self.root, stdout=subprocess.PIPE, check=True
        ).stdout


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
        before = self.start if self.added_rows else self.start + 1
        line = min(self.points) if self.points else self.deletion_point
        return Removal(before, line, tuple(self.removed), tuple(self.removed_lines))

    def add(self, text: str) -> None:
        # A blank line changes nothing in any language, so only lines holding code count.
        if _holds_code(text):
            self.points.add(self.start + self.added_rows)
        self.added_rows += 1

    def remove(self, text: str) -> None:
        if _holds_code(text):
            # Shown to the judge, so a byte that isn't UTF-8 becomes U+FFFD, as in the file.
            row = text.removesuffix("\r").encode(errors="surrogateescape")
            self.removed.append(row.decode(errors="replace"))
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


def _holds_code(text: str) -> bool:
    return bool(text.strip(_BLANK))


def _frozen(points: dict[str, set[int]]) -> dict[str, frozenset[int]]:
    return {file: frozenset(numbers) for file, numbers in points.items()}


def _run_git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, stdout=subprocess.PIPE, text=True, check=True
    ).stdout
