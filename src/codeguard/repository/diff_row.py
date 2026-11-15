from dataclasses import dataclass
from typing import Self

_GIT_BLANK = b" \t\r\f\v"


@dataclass(frozen=True)
class RowText:
    content: bytes

    @classmethod
    def of_line(cls, line: bytes) -> Self:
        return cls(line.removesuffix(b"\n").removesuffix(b"\r"))

    @property
    def holds_code(self) -> bool:
        return bool(self.content.strip(_GIT_BLANK))


@dataclass(frozen=True)
class KeptRow:
    base_line: int
    head_line: int

    @property
    def kept_head_line(self) -> int | None:
        return self.head_line


@dataclass(frozen=True)
class AddedRow:
    head_line: int
    text: RowText

    @property
    def kept_head_line(self) -> int | None:
        return None


@dataclass(frozen=True)
class RemovedRow:
    base_line: int
    text: RowText

    @property
    def kept_head_line(self) -> int | None:
        return None


type DiffRow = KeptRow | AddedRow | RemovedRow
