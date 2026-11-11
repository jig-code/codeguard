import re
from dataclasses import dataclass

_HEADER = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_COUNT_WHEN_OMITTED = 1


@dataclass(frozen=True)
class Hunk:
    file: str
    base_file: str | None
    base_start: int
    base_count: int
    start: int
    count: int
    added: tuple[str, ...]
    removed: tuple[str, ...]

    @property
    def line_before(self) -> int:
        # git gives an empty side the number of the line before it.
        return self.start if self.count == 0 else self.start - 1


def parse(unprefixed_diff: str) -> tuple[Hunk, ...]:
    hunks: list[Hunk] = []
    file = ""
    base_file: str | None = None
    header: re.Match[str] | None = None
    added: list[str] = []
    removed: list[str] = []
    for row in [*unprefixed_diff.split("\n"), "diff --git "]:
        if (row.startswith("diff --git ") or _HEADER.match(row)) and header:
            hunks.append(_hunk(file, base_file, header, added, removed))
            header, added, removed = None, [], []
        if row.startswith("diff --git "):
            file, base_file = "", None
        elif header is None and row.startswith("--- "):
            # git ends a name holding a space with a tab.
            name = row.removeprefix("--- ").removesuffix("\t")
            base_file = None if name == "/dev/null" else name
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
    file: str, base_file: str | None, header: re.Match[str], added: list[str], removed: list[str]
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
    return _COUNT_WHEN_OMITTED if group is None else int(group)
