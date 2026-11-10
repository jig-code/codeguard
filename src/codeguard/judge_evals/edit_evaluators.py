from dataclasses import dataclass

from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext

from codeguard.config import ChangeKind
from codeguard.rule_tests import EditCase, EditReview, Outcome


@dataclass
class PartialEqualsExpected(Evaluator[EditCase, EditReview, None]):
    def evaluate(
        self, ctx: EvaluatorContext[EditCase, EditReview, None]
    ) -> EvaluationReason | dict[str, bool]:
        if ctx.expected_output is None:
            return {}
        expected = _listed(ctx.expected_output, ctx.expected_output)
        actual = _listed(ctx.output, ctx.expected_output)
        if actual == expected:
            return EvaluationReason(value=True)
        return EvaluationReason(
            value=False,
            reason=f"expected {_described(expected)}, got {_described(actual)}{ctx.output.listing}",
        )


@dataclass
class ViolationsOnTriggers(Evaluator[EditCase, EditReview, None]):
    triggers: tuple[str, ...]
    confidence_threshold: float

    def evaluate(
        self, ctx: EvaluatorContext[EditCase, EditReview, None]
    ) -> EvaluationReason | dict[str, bool]:
        expected = ctx.expected_output.outcome if ctx.expected_output else None
        if (
            expected is not Outcome.INVALID
            or ctx.output.outcome is not Outcome.INVALID
            or ChangeKind.ANY in self.triggers
        ):
            return {}
        kinds = {
            violation.lines.start: violation.kinds
            for violation in ctx.output.violations
            if violation.confidence >= self.confidence_threshold and violation.kinds is not None
        }
        if not kinds or any(set(self.triggers) & set(found) for found in kinds.values()):
            return EvaluationReason(value=True)
        lines = ", ".join(map(str, sorted(kinds)))
        on_lines = ", ".join(sorted({kind for found in kinds.values() for kind in found}))
        return EvaluationReason(
            value=False,
            reason=f"violation on line {lines} is outside the triggers {', '.join(self.triggers)}\n"
            f"  Add one of the kinds on that line to triggers in its binding: {on_lines}",
        )


def _described(fields: dict[str, object]) -> str:
    return ", ".join(f"{name} {value}" for name, value in fields.items())


def _listed(review: EditReview, expected: EditReview) -> dict[str, object]:
    # The judge's reason is context for whoever reads the eval, printed with it, never compared.
    listed = expected.model_fields_set - {"reason"}
    fields: dict[str, object] = review.model_dump(mode="json", include=listed - {"violations"})
    if "violations" in listed:
        fields["violations"] = [
            violation.model_dump(mode="json", include=_violation_fields(expected, index))
            for index, violation in enumerate(review.violations)
        ]
    return fields


def _violation_fields(expected: EditReview, index: int) -> set[str]:
    if index < len(expected.violations):
        return set(expected.violations[index].model_fields_set)
    return {name for violation in expected.violations for name in violation.model_fields_set}
