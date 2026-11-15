from dataclasses import dataclass
from pathlib import Path
from typing import Self


@dataclass(frozen=True)
class JudgeRule:
    name: str
    text: str

    @classmethod
    def from_file(cls, name: str, file: Path) -> Self:
        return cls(name=name, text=file.read_text())
