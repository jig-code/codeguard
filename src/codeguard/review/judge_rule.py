import re
from dataclasses import dataclass

# A `## Why` heading followed by text before the next heading of its level or above.
_WHY_SECTION = re.compile(r"^##[ \t]+Why[ \t]*\n(?P<body>(?:(?!#{1,2}[ \t]).*\n?)*)", re.MULTILINE)
_HEADING = re.compile(r"^#{1,6}[ \t]")
_TITLE = re.compile(r"^#[ \t]+\S")
_WHY_HEADING = re.compile(r"^##[ \t]+Why[ \t]*$")
_FENCE = "```"


@dataclass(frozen=True)
class JudgeRule:
    name: str
    text: str

    @property
    def says_why(self) -> bool:
        match = _WHY_SECTION.search(self.text)
        return match is not None and bool(match.group("body").strip())

    def format_problems(self) -> tuple[str, ...]:
        """What keeps the text from being a title, a statement and `## Why`, in that order."""
        lines = self.text.splitlines()
        if not lines or not _TITLE.match(lines[0]):
            return ("must start with a `# ` title",)
        headings = self._headings(lines[1:])
        return (
            *(
                f"has the heading {heading!r}, but holds only a title, the statement and `## Why`"
                for heading in headings
                if not _WHY_HEADING.match(heading)
            ),
            *(() if self._statement(lines[1:]) else ("has no statement under its title",)),
            *(() if self.says_why else ("has no `## Why` section with text",)),
        )

    @staticmethod
    def _headings(lines: list[str]) -> list[str]:
        inside_fence = False
        headings: list[str] = []
        for line in lines:
            if line.lstrip().startswith(_FENCE):
                inside_fence = not inside_fence
            elif not inside_fence and _HEADING.match(line):
                headings.append(line)
        return headings

    @staticmethod
    def _statement(lines: list[str]) -> str:
        first_heading = next((i for i, line in enumerate(lines) if _HEADING.match(line)), None)
        return "\n".join(lines[:first_heading]).strip()
