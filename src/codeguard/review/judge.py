import json
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import InlineDefsJsonSchemaTransformer
from pydantic_ai.tools import GenerateToolJsonSchema

from codeguard.line_range import LineRange
from codeguard.repository import LineScope, WorkingTree
from codeguard.review.binding import Binding
from codeguard.review.diagnostic import Category, Diagnostic, ErrorType
from codeguard.review.judge_rule import JudgeRule
from codeguard.syntax import Classification

DEFAULT_MODEL_KEY = "default"
DEFAULT_THINKING_KEY = "default"
INSTRUCTIONS = (Path(__file__).parent / "judge.md").read_text()


@dataclass(frozen=True)
class JudgeRequest:
    judge_rule: JudgeRule
    file: str
    changes: str

    @classmethod
    def of_change(
        cls,
        binding: Binding,
        working_tree: WorkingTree,
        file: str,
        scope: LineScope,
        classification: Classification,
    ) -> Self:
        raw = working_tree.contents(file).splitlines()
        content = [_decoded_for_judge(line) for line in raw]
        lines = classification.judged_lines(file, binding.triggers)
        shown = set(range(1, len(content) + 1) if lines is None else lines)
        added = scope.added_lines(file)
        removals = {removal.shown_before: removal for removal in scope.removals_in(file)}
        rows: list[str] = []
        for number in sorted(shown | set(removals)):
            if removal := removals.get(number):
                rows.extend(
                    f"-{removal.reported_line:>6}\t{_decoded_for_judge(row.text.content)}\n"
                    for row in removal.rows
                )
            if number in shown and number <= len(content):
                mark = "+" if added is None or number in added else " "
                rows.append(f"{mark}{number:>6}\t{content[number - 1]}\n")
        return cls(binding.judge_rule, file, "".join(rows))

    @property
    def instructions(self) -> str:
        return INSTRUCTIONS

    @property
    def prompt(self) -> str:
        return (
            f'<rule name="{self.judge_rule.name}">\n{self.judge_rule.text}</rule>\n\n'
            f'<changes path="{self.file}">\n{self.changes}</changes>\n'
        )


def _decoded_for_judge(row: bytes) -> str:
    return row.decode(errors="replace")


class Violation(BaseModel):
    """A violation of the rule that a `+` or `-` line of the change is part of."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    file: str = Field(
        description="The file under review's path, exactly as the `changes` element gives it."
    )
    lines: LineRange = Field(
        description=(
            "The first and last line of the code that breaks the rule, numbered as the "
            "`changes` element numbers them."
        )
    )
    message: str = Field(description="What breaks the rule, in one plain sentence.")


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

    def diagnostics_for(self, binding: Binding, file: str) -> tuple[Diagnostic, ...]:
        return tuple(
            Diagnostic(
                rule=binding.rule,
                file=violation.file,
                lines=violation.lines,
                message=violation.message,
                severity=binding.severity,
                note=None,
                category=Category.JUDGED,
            )
            for violation in self.violations
            if violation.file == file
        )


VERDICT_SCHEMA = json.dumps(
    InlineDefsJsonSchemaTransformer(
        Verdict.model_json_schema(schema_generator=GenerateToolJsonSchema)
    ).walk()
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
