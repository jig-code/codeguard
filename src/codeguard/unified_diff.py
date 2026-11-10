import re
from dataclasses import dataclass

_HEADER = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


@dataclass(frozen=True)
class Hunk:
    """One hunk of a unified diff: `base_count` rows from line `base_start` of `base_file`
    replaced by `count` rows from line `start` of `file`. git numbers an empty side by the
    line before it. `base_file` is empty for a new file."""

    file: str
    base_file: str
    base_start: int
    base_count: int
    start: int
    count: int
    added: tuple[str, ...]
    removed: tuple[str, ...]


def parse(diff: str) -> tuple[Hunk, ...]:
    """The hunks of a diff git wrote without prefixes, each with the rows it adds and
    removes. Only "\\n" ends a row."""
    hunks: list[Hunk] = []
    file = base_file = ""
    header: re.Match[str] | None = None
    added: list[str] = []
    removed: list[str] = []
    for row in [*diff.split("\n"), "diff --git "]:
        if (row.startswith("diff --git ") or _HEADER.match(row)) and header:
            hunks.append(_hunk(file, base_file, header, added, removed))
            header, added, removed = None, [], []
        if row.startswith("diff --git "):
            file = base_file = ""
        elif header is None and row.startswith("--- "):
            # git ends the name with a tab when it holds a space.
            name = row.removeprefix("--- ").removesuffix("\t")
            base_file = "" if name == "/dev/null" else name
        elif header is None and row.startswith("+++ "):
            file = row.removeprefix("+++ ").removesuffix("\t")
        elif match := _HEADER.match(row):
            header = match
        elif header and row.startswith("-"):
            removed.append(row[1:])
        elif header and row.startswith("+"):
            added.append(row[1:])
    return tuple(hunks)


def _hunk(
    file: str, base_file: str, header: re.Match[str], added: list[str], removed: list[str]
) -> Hunk:
    base_start, base_count, start, count = header.groups()
    return Hunk(
        file=file,
        base_file=base_file,
        base_start=int(base_start),
        base_count=_count(base_count),
        start=int(start),
        count=_count(count),
        added=tuple(added),
        removed=tuple(removed),
    )


def _count(group: str | None) -> int:
    # git leaves out a count of 1.
    return 1 if group is None else int(group)
