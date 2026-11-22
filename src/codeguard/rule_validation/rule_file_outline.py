import re
from dataclasses import dataclass
from typing import Self

_HEADING = re.compile(r"^(?P<marks>#{1,6})[ \t]+(?P<title>\S.*?)[ \t]*$")
_FENCE = "```"
_WHY_HEADING = "## Why"


@dataclass(frozen=True)
class _Section:
    level: int
    title: str
    body: str

    @property
    def is_why(self) -> bool:
        return self.heading == _WHY_HEADING

    @property
    def heading(self) -> str:
        return f"{'#' * self.level} {self.title}"


@dataclass(frozen=True)
class RuleFileOutline:
    """A `#` line in a code fence is a comment in the code, not a heading."""

    preamble: str
    sections: tuple[_Section, ...]

    @classmethod
    def from_text(cls, text: str) -> Self:
        preamble: list[str] = []
        headings: list[tuple[int, str]] = []
        bodies: list[list[str]] = []
        inside_fence = False
        for line in text.splitlines():
            if line.lstrip().startswith(_FENCE):
                inside_fence = not inside_fence
            heading = None if inside_fence else _HEADING.match(line)
            if heading:
                headings.append((len(heading["marks"]), heading["title"]))
                bodies.append([])
            else:
                (bodies[-1] if bodies else preamble).append(line)
        return cls(
            "\n".join(preamble),
            tuple(
                _Section(level, title, "\n".join(lines))
                for (level, title), lines in zip(headings, bodies, strict=True)
            ),
        )

    @property
    def says_why(self) -> bool:
        in_why = False
        for section in self.sections:
            in_why = section.is_why or (in_why and section.level > 2)
            if in_why and section.body.strip():
                return True
        return False

    def format_problems(self) -> tuple[str, ...]:
        if self.preamble.strip() or not self.sections or self.sections[0].level != 1:
            return ("must start with a `# ` title",)
        title, *rest = self.sections
        return (
            *(
                f"has the heading {section.heading!r}, but holds only a title, the statement "
                f"and `{_WHY_HEADING}`"
                for section in rest
                if not section.is_why
            ),
            *(() if title.body.strip() else ("has no statement under its title",)),
            *(() if self.says_why else (f"has no `{_WHY_HEADING}` section with text",)),
        )
