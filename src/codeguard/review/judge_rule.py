import re
from dataclasses import dataclass

# A `## Why` heading followed by text before the next heading of its level or above.
_WHY_SECTION = re.compile(r"^##[ \t]+Why[ \t]*\n(?P<body>(?:(?!#{1,2}[ \t]).*\n?)*)", re.MULTILINE)


@dataclass(frozen=True)
class JudgeRule:
    name: str
    text: str

    @property
    def says_why(self) -> bool:
        match = _WHY_SECTION.search(self.text)
        return match is not None and bool(match.group("body").strip())
