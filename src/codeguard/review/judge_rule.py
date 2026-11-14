import re
from dataclasses import dataclass
from pathlib import Path
from typing import Self

_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


@dataclass(frozen=True)
class Skill:
    name: str
    text: str

    @classmethod
    def from_file(cls, name: str, file: Path) -> Self:
        return cls(name=name, text=_FRONTMATTER.sub("", file.read_text(), count=1))
