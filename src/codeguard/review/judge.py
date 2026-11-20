from dataclasses import dataclass
from enum import ReprEnum
from pathlib import Path
from typing import ClassVar, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter
from pydantic_ai.tools import GenerateToolJsonSchema

from codeguard.line_range import LineRange
from codeguard.repository import LineScope, WorkingTree
from codeguard.review.binding import Binding
from codeguard.review.diagnostic import Category, Diagnostic, ErrorType, Severity
from codeguard.review.judge_rule import JudgeRule
from codeguard.syntax import Classification

DEFAULT_MODEL_KEY = "default"
DEFAULT_THINKING_KEY = "default"
INSTRUCTIONS = (Path(__file__).parent / "judge.md").read_text()
_JSON_OBJECT = TypeAdapter(dict[str, JsonValue])


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


# The likelihood levels the judge rates a violation with. The schema gives the model only these
# values, so a confidence between two of them can't reach the threshold check;
# `Violation.confidence`'s description says what each value means. A plain enum's schema is one
# `enum` beside its `type`, which every provider's strict mode accepts: pydantic-ai doesn't make
# a described `const` per member strict-safe for Bedrock.
class Confidence(float, ReprEnum):
    """How certain you are that the code breaks the rule."""

    CERTAIN = 1.0
    HIGHLY_PROBABLE = 0.9
    PROBABLE = 0.7
    POSSIBLE = 0.5


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
    confidence: Confidence = Field(
        description=(
            "How certain you are that the code breaks the rule. Use one of these values, not "
            "one between them. 1.0: You are certain: what the code does is what the rule "
            "forbids, and nothing in the working directory points to an exception the rule "
            "allows. 0.9: The code breaks the rule as written, but the verdict rests on a "
            "reading of the rule's terms a reviewer could contest. You would still block the "
            "change. 0.7: The code probably breaks the rule, but something in the working "
            "directory points to an exception the rule allows. 0.5: The code is as likely to "
            "follow the rule as to break it. Below 0.5 the code probably follows the rule: "
            "don't report it. An unseen caller, implementer, or fixture is not a reason to "
            "lower it. Lower it only for something you can point to in the working directory. "
            "When what the code does shows the violation, a name that says nothing is not a "
            "reason to lower it. Give the same file the same confidence each time you judge it."
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
                lines=violation.lines,
                message=violation.message,
                severity=violation.severity(binding.severity, threshold),
                note=None,
                category=Category.JUDGED,
                confidence=violation.confidence,
            )
            for violation in self.violations
            if violation.file == file
        )


def output_schema(output: type[BaseModel]) -> dict[str, JsonValue]:
    """The schema pydantic-ai's generator gives the API judge, with every `$ref` inlined and each
    field's description kept. Claude Code's `--json-schema` enforces a schema strictly only when it
    has no `$ref` or `$defs`, and Codex's strict validator needs references inlined too.
    """
    schema = _JSON_OBJECT.validate_python(
        output.model_json_schema(schema_generator=GenerateToolJsonSchema)
    )
    definitions = schema.pop("$defs", {})
    if not isinstance(definitions, dict):
        raise ValueError(f"{output.__name__}'s schema definitions must be objects")
    return {key: _inlined(value, definitions) for key, value in schema.items()}


def _inlined(value: JsonValue, definitions: dict[str, JsonValue]) -> JsonValue:
    if isinstance(value, list):
        return [_inlined(item, definitions) for item in value]
    if not isinstance(value, dict):
        return value
    reference = value.get("$ref")
    if isinstance(reference, str):
        definition = definitions[reference.removeprefix("#/$defs/")]
        if not isinstance(definition, dict):
            raise ValueError(f"Schema reference {reference} must name an object")
        value = {**definition, **{key: item for key, item in value.items() if key != "$ref"}}
    return {key: _inlined(item, definitions) for key, item in value.items()}


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
