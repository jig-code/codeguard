import re
from dataclasses import dataclass
from typing import Self

from codeguard.config import BindingConfig, Ruleset

_WHY_HEADING = r"##[ \t]+Why[ \t]*"
# A `## Why` heading followed by text before the next heading of its level or above.
_WHY_SECTION = re.compile(rf"^{_WHY_HEADING}\n(?P<body>(?:(?!#{{1,2}}[ \t]).*\n?)*)", re.MULTILINE)
_HEADING = re.compile(r"^#{1,6}[ \t]")
_TITLE = re.compile(r"^#[ \t]+\S")
_WHY_HEADING_LINE = re.compile(rf"^{_WHY_HEADING}$")
_FENCE = "```"


@dataclass(frozen=True)
class JudgeRule:
    name: str
    text: str

    @classmethod
    def from_binding(cls, binding: BindingConfig, ruleset: Ruleset) -> Self:
        return cls(name=binding.rule_id, text=ruleset.judge_rule_text(binding))

    @property
    def says_why(self) -> bool:
        match = _WHY_SECTION.search(self.text)
        return match is not None and bool(match.group("body").strip())

    def format_problems(self) -> tuple[str, ...]:
        """What keeps the text from being a title, a statement and `## Why`, in that order."""
        lines = self.text.splitlines()
        if not lines or not _TITLE.match(lines[0]):
            return ("must start with a `# ` title",)
        body = lines[1:]
        headings = _heading_rows(body)
        statement = body[: headings[0][0]] if headings else body
        return (
            *(
                f"has the heading {heading!r}, but holds only a title, the statement and `## Why`"
                for _, heading in headings
                if not _WHY_HEADING_LINE.match(heading)
            ),
            *(() if "".join(statement).strip() else ("has no statement under its title",)),
            *(() if self.says_why else ("has no `## Why` section with text",)),
        )


def _heading_rows(lines: list[str]) -> list[tuple[int, str]]:
    inside_fence = False
    rows: list[tuple[int, str]] = []
    for row, line in enumerate(lines):
        if line.lstrip().startswith(_FENCE):
            inside_fence = not inside_fence
        elif not inside_fence and _HEADING.match(line):
            rows.append((row, line))
    return rows
