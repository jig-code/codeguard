from dataclasses import dataclass
from enum import ReprEnum
from pathlib import Path
from typing import ClassVar, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field
from pydantic.json_schema import JsonSchemaValue
from pydantic_ai import UseEnumMemberDocstrings
from pydantic_ai.tools import GenerateToolJsonSchema

from codeguard.review.binding import Binding
from codeguard.review.diagnostic import Category, Diagnostic, ErrorType, Severity
from codeguard.review.skill import Skill
from codeguard.working_tree import AllLines, ChangedLines

DEFAULT_MODEL_KEY = "default"
INSTRUCTIONS = (Path(__file__).parent / "judge.md").read_text()


@dataclass(frozen=True)
class JudgeRequest:
    skill: Skill
    file: str
    changes: str

    @classmethod
    def of_change(
        cls, binding: Binding, root: Path, file: str, scope: ChangedLines | AllLines
    ) -> Self:
        raw = (root / file).read_bytes().splitlines()
        content = [line.decode(errors="replace") for line in raw]
        lines = scope.judged_lines(file, binding.triggers)
        shown = set(range(1, len(content) + 1) if lines is None else lines)
        added = scope.added_lines(file)
        removals = {removal.before: removal for removal in scope.removals_in(file)}
        rows: list[str] = []
        for number in sorted(shown | set(removals)):
            if removal := removals.get(number):
                rows.extend(f"-{removal.line:>6}\t{text}\n" for text in removal.rows)
            if number in shown and number <= len(content):
                mark = "+" if added is None or number in added else " "
                rows.append(f"{mark}{number:>6}\t{content[number - 1]}\n")
        return cls(binding.skill_for(file), file, "".join(rows))

    @property
    def instructions(self) -> str:
        return INSTRUCTIONS

    @property
    def prompt(self) -> str:
        return (
            f'<rule name="{self.skill.name}">\n{self.skill.text}</rule>\n\n'
            f'<changes path="{self.file}">\n{self.changes}</changes>\n'
        )


# The likelihood levels the judge rates a violation with. The schema gives the model only these
# values, so a confidence between two of them can't reach the threshold check, and describes each
# value by the docstring under it. pydantic-ai reads the docstrings from the source, as one string
# literal under each member, and only `output_schema` includes them.
class Confidence(UseEnumMemberDocstrings, float, ReprEnum):
    """How certain you are that the code breaks the rule."""

    CERTAIN = 1.0
    (
        "You are certain: what the code does is what the rule forbids, and nothing in the "
        "working directory points to an exception the rule allows."
    )
    HIGHLY_PROBABLE = 0.9
    (
        "The code breaks the rule as written, but the verdict rests on a reading of the rule's "
        "terms a reviewer could contest. You would still block the change."
    )
    PROBABLE = 0.7
    (
        "The code probably breaks the rule, but something in the working directory points to an "
        "exception the rule allows."
    )
    POSSIBLE = 0.5
    "The code is as likely to follow the rule as to break it."


class Violation(BaseModel):
    """A violation of the rule that a `+` or `-` line of the change is part of."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    file: str = Field(
        description="The file under review's path, exactly as the `changes` element gives it."
    )
    line: int = Field(description="The number of a `+` or `-` line that is part of the violation.")
    message: str = Field(description="What breaks the rule, in one plain sentence.")
    confidence: Confidence = Field(
        description=(
            "How certain you are that the code breaks the rule. Use one of these values, not "
            "one between them. Below 0.5 the code probably follows the rule: don't report it."
        ),
    )

    def severity(self, severity: Severity, threshold: float) -> Severity:
        if severity is Severity.ERROR and self.confidence < threshold:
            return Severity.WARNING
        return severity


class Verdict(BaseModel):
    """Why the change passes or fails the rule, and the violations it is part of."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    reason: str = Field(
        description=(
            "Why the change passes or fails, in one plain sentence: what in the changed code "
            "keeps the rule, or what in it breaks the rule."
        )
    )
    violations: tuple[Violation, ...] = Field(
        description="Each violation of the rule; none when the code follows it."
    )

    def diagnostics_for(
        self, binding: Binding, file: str, threshold: float
    ) -> tuple[Diagnostic, ...]:
        return tuple(
            Diagnostic(
                rule=binding.rule,
                file=violation.file,
                line=violation.line,
                message=violation.message,
                severity=violation.severity(binding.severity, threshold),
                note=None,
                category=Category.JUDGED,
                confidence=violation.confidence,
            )
            for violation in self.violations
            if violation.file == file
        )


def output_schema(output: type[BaseModel]) -> JsonSchemaValue:
    """The schema of what the model answers with, as a provider sends it to the model.

    pydantic-ai's generator describes each `Confidence` value by its docstring; Pydantic's own
    `model_json_schema` leaves the docstrings out. The Gemini provider gets this schema from
    pydantic-ai itself, which uses the same generator.
    """
    return output.model_json_schema(schema_generator=GenerateToolJsonSchema)


@dataclass(frozen=True)
class Judgement:
    verdict: Verdict
    loaded_files: tuple[str, ...] = ()


class JudgeError(Exception):
    error_type: ClassVar[ErrorType]


class JudgeTimeout(JudgeError):
    error_type = ErrorType.TIMEOUT


class JudgeProcessError(JudgeError):
    error_type = ErrorType.PROCESS


class JudgeNoVerdict(JudgeError):
    error_type = ErrorType.NO_VERDICT


class Judge(Protocol):
    @property
    def identity(self) -> str: ...

    def judge(self, request: JudgeRequest) -> Judgement: ...
