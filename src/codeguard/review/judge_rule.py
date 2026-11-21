import re
from dataclasses import dataclass
from typing import Self

from codeguard.config import BindingConfig, Ruleset

_HEADING = re.compile(r"^(?P<marks>#{1,6})[ \t]+(?P<title>\S.*?)[ \t]*$")
_FENCE = "```"
_WHY = "Why"


@dataclass(frozen=True)
class _Section:
    level: int
    title: str
    body: str

    @property
    def is_why(self) -> bool:
        return self.level == 2 and self.title == _WHY

    @property
    def heading(self) -> str:
        return f"{'#' * self.level} {self.title}"


@dataclass(frozen=True)
class _Outline:
    """The text split at its headings, ignoring any inside a code fence. The first
    section is the text before the first heading, at level 0."""

    sections: tuple[_Section, ...]

    @classmethod
    def of(cls, text: str) -> Self:
        headings = [(0, "")]
        bodies: list[list[str]] = [[]]
        inside_fence = False
        for line in text.splitlines():
            if line.lstrip().startswith(_FENCE):
                inside_fence = not inside_fence
            heading = None if inside_fence else _HEADING.match(line)
            if heading:
                headings.append((len(heading["marks"]), heading["title"]))
                bodies.append([])
            else:
                bodies[-1].append(line)
        return cls(
            tuple(
                _Section(level, title, "\n".join(lines))
                for (level, title), lines in zip(headings, bodies, strict=True)
            )
        )

    @property
    def starts_with_title(self) -> bool:
        return (
            not self.sections[0].body.strip()
            and len(self.sections) > 1
            and (self.sections[1].level == 1)
        )

    @property
    def statement(self) -> str:
        return self.sections[1].body.strip() if self.starts_with_title else ""

    @property
    def sections_after_title(self) -> tuple[_Section, ...]:
        return self.sections[2:] if self.starts_with_title else ()

    @property
    def why(self) -> str:
        texts: list[str] = []
        in_why = False
        for section in self.sections[1:]:
            in_why = section.is_why or (in_why and section.level > 2)
            if in_why:
                texts.append(section.body)
        return "".join(texts)


@dataclass(frozen=True)
class JudgeRule:
    name: str
    text: str

    @classmethod
    def from_binding(cls, binding: BindingConfig, ruleset: Ruleset) -> Self:
        return cls(name=binding.rule_id, text=ruleset.judge_rule_text(binding))

    @classmethod
    def rule_files_of(cls, ruleset: Ruleset) -> tuple[Self, ...]:
        return cls._of(ruleset, legacy_skills=False)

    @classmethod
    def legacy_skills_of(cls, ruleset: Ruleset) -> tuple[Self, ...]:
        return cls._of(ruleset, legacy_skills=True)

    @classmethod
    def _of(cls, ruleset: Ruleset, *, legacy_skills: bool) -> tuple[Self, ...]:
        rules = (
            cls.from_binding(binding, ruleset)
            for binding in ruleset.selected_bindings().values()
            if binding.is_legacy_skill == legacy_skills
        )
        return tuple(sorted(rules, key=lambda rule: rule.name))

    @property
    def says_why(self) -> bool:
        return bool(_Outline.of(self.text).why.strip())

    def format_problems(self) -> tuple[str, ...]:
        outline = _Outline.of(self.text)
        if not outline.starts_with_title:
            return ("must start with a `# ` title",)
        return (
            *(
                f"has the heading {section.heading!r}, but holds only a title, the statement "
                "and `## Why`"
                for section in outline.sections_after_title
                if not section.is_why
            ),
            *(() if outline.statement else ("has no statement under its title",)),
            *(() if outline.why.strip() else ("has no `## Why` section with text",)),
        )
