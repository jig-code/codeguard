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
        """What keeps the file from being a title, a statement and `## Why`, in that order."""
        lines = self.text.splitlines()
        if not lines or not _TITLE.match(lines[0]):
            return ("must start with a `# ` title",)
        body = lines[1:]
        headings = [line for line in _outside_fences(body) if _HEADING.match(line)]
        problems = [
            f"has the heading {heading!r}, but holds only a title, the statement and `## Why`"
            for heading in headings
            if not _WHY_HEADING.match(heading)
        ]
        statement = _until_first_heading(body)
        if not statement.strip():
            problems.append("has no statement between its title and `## Why`")
        return tuple(problems)


def _outside_fences(lines: list[str]) -> list[str]:
    inside = False
    outside: list[str] = []
    for line in lines:
        if line.lstrip().startswith(_FENCE):
            inside = not inside
        elif not inside:
            outside.append(line)
    return outside


def _until_first_heading(lines: list[str]) -> str:
    for index, line in enumerate(lines):
        if _HEADING.match(line):
            return "\n".join(lines[:index])
    return "\n".join(lines)
