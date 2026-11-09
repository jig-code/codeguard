import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Self

_HUNK = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
# ASCII whitespace, the same set git treats as blank.
_BLANK = " \t\r\f\v"
# Every option the user's git config could change is pinned, so the judge gets the same diff
# on every machine (invariant #5). The attributes file gives each language git has a built-in
# diff driver for that driver, so function context is the changed function, not the class
# around it; a repository's own attributes still take precedence.
_DIFF = (
    "-c",
    "core.quotePath=false",
    "-c",
    f"core.attributesFile={Path(__file__).parent / 'diff_drivers.gitattributes'}",
    "-c",
    "diff.interHunkContext=0",
    "-c",
    "diff.suppressBlankEmpty=false",
    "diff",
    "--no-color",
    "--no-ext-diff",
    "--no-textconv",
    "--no-relative",
    "--diff-algorithm=myers",
    "--indent-heuristic",
    "--unified=3",
    "--function-context",
    "--src-prefix=a/",
    "--dst-prefix=b/",
)


@dataclass(frozen=True)
class Edit:
    """A hunk: `base_count` rows from line `base_start` of the base replaced by `count` rows
    from line `start`. git numbers an empty side by the line before it."""

    base_start: int
    base_count: int
    start: int
    count: int


@dataclass(frozen=True)
class ChangedLines:
    lines: Mapping[str, frozenset[int]]
    deletions: Mapping[str, frozenset[int]] = field(default_factory=dict)
    kinds: Mapping[str, frozenset[str]] = field(default_factory=dict)
    removed: Mapping[str, frozenset[int]] = field(default_factory=dict)
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

    def removed_lines(self, file: str) -> frozenset[int]:
        """The base lines holding code that the change removed."""
        return self.removed.get(file, frozenset())

    def kinds_of(self, file: str) -> frozenset[str] | None:
        return self.kinds.get(file)

    def base_path(self, file: str) -> str | None:
        """The file's path in the base, which a rename changes; None for a file git's diff
        doesn't hold, which is untracked, so new."""
        if file not in self.edits:
            return None
        return self.sources.get(file, file)

    def diff(self, root: Path, file: str) -> str:
        base_path = self.base_path(file)
        if self.base is None or base_path is None:
            return WorkingTree(root).new_file_diff(file)
        return WorkingTree(root).diff(self.base, base_path, file)

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

    def diff(self, root: Path, file: str) -> str:
        return WorkingTree(root).new_file_diff(file)


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
            removed=_removed(hunks),
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

    def diff(self, base: str, base_path: str, file: str) -> str:
        """git's diff of the file from the base, with the function around each change."""
        paths = (file,) if base_path == file else (base_path, file)
        return self._diff_text(self._git_bytes(*_DIFF, "--find-renames", base, "--", *paths))

    def new_file_diff(self, file: str) -> str:
        """git's diff of the whole file as added."""
        diff = subprocess.run(
            ["git", *_DIFF, "--no-index", "--", "/dev/null", file],
            cwd=self.root,
            stdout=subprocess.PIPE,
            check=False,
        )
        if diff.returncode > 1:
            raise subprocess.CalledProcessError(diff.returncode, diff.args)
        return self._diff_text(diff.stdout)

    def all_lines(self) -> AllLines:
        listed = self._git_paths("ls-files", "--cached", "--others", "--exclude-standard")
        return AllLines(tuple(sorted(path for path in listed if (self.root / path).is_file())))

    def git_path(self, name: str) -> Path:
        return self.root / self._git("rev-parse", "--git-path", name).strip()

    def _code_lines(self, file: str) -> frozenset[int]:
        lines = _rows((self.root / file).read_bytes())
        return frozenset(number for number, text in enumerate(lines, 1) if _holds_code(text))

    @staticmethod
    def _diff_text(diff: bytes) -> str:
        # Sent to the judge, so a byte that isn't UTF-8 becomes U+FFFD.
        return diff.decode(errors="replace")

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
        if not hunk.points and hunk.removed_lines:
            deletions[hunk.file].add(hunk.deletion_point)
    return _frozen(added), _frozen(deletions)


def _removed(hunks: Sequence["_Hunk"]) -> dict[str, frozenset[int]]:
    removed: dict[str, set[int]] = {}
    for hunk in hunks:
        if hunk.removed_lines:
            removed.setdefault(hunk.file, set()).update(hunk.removed_lines)
    return _frozen(removed)


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
    removed_lines: list[int] = field(default_factory=list)

    @property
    def edit(self) -> Edit:
        return Edit(self.base_start, self.base_count, self.start, self.count)

    @property
    def deletion_point(self) -> int:
        return max(self.start - 1 if self.added_rows else self.start, 1)

    def add(self, text: str) -> None:
        # A blank line changes nothing in any language, so only lines holding code count.
        if _holds_code(text):
            self.points.add(self.start + self.added_rows)
        self.added_rows += 1

    def remove(self, text: str) -> None:
        if _holds_code(text):
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
