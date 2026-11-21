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
        lines = self.text.splitlines()
        if not lines or not _TITLE.match(lines[0]):
            return ("must start with a `# ` title",)
        return (
            *(
                f"has the heading {heading!r}, but holds only a title, the statement and `## Why`"
                for heading in self._headings(lines[1:])
                if not _WHY_HEADING_LINE.match(heading)
            ),
            *(() if self._has_statement(lines[1:]) else ("has no statement under its title",)),
            *(() if self.says_why else ("has no `## Why` section with text",)),
        )

    @staticmethod
    def _has_statement(lines_under_title: list[str]) -> bool:
        first = next((line for line in lines_under_title if line.strip()), "")
        return bool(first) and not _HEADING.match(first)

    @staticmethod
    def _headings(lines_under_title: list[str]) -> list[str]:
        inside_fence = False
        headings: list[str] = []
        for line in lines_under_title:
            if line.lstrip().startswith(_FENCE):
                inside_fence = not inside_fence
            elif not inside_fence and _HEADING.match(line):
                headings.append(line)
        return headings
