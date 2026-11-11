from dataclasses import dataclass


@dataclass(frozen=True)
class Removal:
    shown_before: int
    reported_line: int
    rows: tuple[str, ...]
    base_lines: tuple[int, ...]
