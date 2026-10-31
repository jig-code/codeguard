from dataclasses import dataclass
from enum import ReprEnum
from pathlib import Path
from typing import ClassVar, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field

from codeguard.review.binding import Binding
from codeguard.review.diagnostic import Category, Diagnostic, ErrorType, Severity
from codeguard.review.skill import Skill
from codeguard.working_tree import AllLines, ChangedLines

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
            f'<convention name="{self.skill.name}">\n{self.skill.text}</convention>\n\n'
            f'<changes path="{self.file}">\n{self.changes}</changes>\n'
        )


# The likelihood levels the judge rates a violation with: how likely it is that the code breaks
# the convention. The schema gives the model only these values, so a confidence between two of
# them can't reach the threshold check.
class Confidence(float, ReprEnum):
    CERTAIN = 1.0
    HIGHLY_PROBABLE = 0.9
    PROBABLE = 0.7
    POSSIBLE = 0.5


class Violation(BaseModel):
    """A violation of the convention that a `+` or `-` line of the change is part of."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    file: str = Field(
        description="The file under review's path, exactly as the `changes` element gives it."
    )
    line: int = Field(description="The number of a `+` or `-` line that is part of the violation.")
    message: str = Field(description="What breaks the convention, in one plain sentence.")
    confidence: Confidence = Field(
        description=(
            "How certain you are that the code breaks the convention. Use one of these values, "
            "not one between them. 1.0: the code matches a case, sign, or example the "
            "convention describes, in substance if not in exact text. 0.9: the code breaks the "
            "convention as written; you would block the change. 0.7: the code probably breaks "
            "the convention, but something in the working directory points to an exception the "
            "convention allows. 0.5: the code is as likely to follow the convention as to break "
            "it. Below 0.5 the code probably follows the convention: don't report it."
        ),
    )

    def severity(self, severity: Severity, threshold: float) -> Severity:
        if severity is Severity.ERROR and self.confidence < threshold:
            return Severity.WARNING
        return severity


class Verdict(BaseModel):
    """The violations of the convention the change is part of."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    violations: tuple[Violation, ...] = Field(
        description="Each violation of the convention; none when the code follows it."
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
