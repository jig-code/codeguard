from pydantic_evals.evaluators import EvaluationReason

from codeguard.judge_evals import PartialEqualsExpected, ViolationsOnTriggers
from codeguard.rule_tests import Outcome


class TestPartialEqualsExpected:
    def test_matching_outcome_passes(self, make_evaluator_context, make_edit_review):
        context = make_evaluator_context(
            expected_output=make_edit_review(outcome=Outcome.VALID),
            output=make_edit_review(outcome=Outcome.VALID, reason="The code keeps it."),
        )

        result = PartialEqualsExpected().evaluate(context)

        assert result == EvaluationReason(value=True)

    def test_other_outcome_fails_with_the_review(self, make_evaluator_context, make_edit_review):
        context = make_evaluator_context(
            expected_output=make_edit_review(outcome=Outcome.INVALID),
            output=make_edit_review(outcome=Outcome.VALID, reason="The code keeps it."),
        )

        result = PartialEqualsExpected().evaluate(context)

        assert result == EvaluationReason(
            value=False,
            reason="expected outcome invalid, got outcome valid\n  reason: The code keeps it.",
        )

    def test_expected_violation_is_compared_only_on_the_fields_it_lists(
        self, make_evaluator_context, make_edit_review, make_judged_violation
    ):
        context = make_evaluator_context(
            expected_output=make_edit_review(violations=(make_judged_violation(),)),
            output=make_edit_review(
                violations=(make_judged_violation(kinds=("call", "string-literal")),)
            ),
        )

        result = PartialEqualsExpected().evaluate(context)

        assert result == EvaluationReason(value=True)

    def test_case_without_an_expected_output_is_not_evaluated(self, make_evaluator_context):
        context = make_evaluator_context(expected_output=None)

        result = PartialEqualsExpected().evaluate(context)

        assert result == {}


class TestViolationsOnTriggers:
    def test_violation_on_a_trigger_passes(
        self, make_evaluator_context, make_edit_review, make_judged_violation
    ):
        context = make_evaluator_context(
            output=make_edit_review(
                violations=(make_judged_violation(kinds=("call", "string-literal")),)
            )
        )

        result = ViolationsOnTriggers(("string-literal",), 0.9).evaluate(context)

        assert result == EvaluationReason(value=True)

    def test_violation_outside_the_triggers_fails_with_the_kinds_on_its_lines(
        self, make_evaluator_context, make_edit_review, make_judged_violation
    ):
        context = make_evaluator_context(
            output=make_edit_review(
                violations=(
                    make_judged_violation(
                        lines__start=2, lines__end=4, kinds=("code", "number-literal")
                    ),
                )
            )
        )

        result = ViolationsOnTriggers(("class-header", "string-literal"), 0.9).evaluate(context)

        assert result == EvaluationReason(
            value=False,
            reason="violation on lines 2-4 is outside the triggers class-header, string-literal\n"
            "  Add one of the kinds on those lines to triggers in its binding: "
            "code, number-literal",
        )

    def test_violation_whose_later_lines_hold_a_trigger_passes_beside_one_sharing_its_first(
        self, make_evaluator_context, make_edit_review, make_judged_violation
    ):
        context = make_evaluator_context(
            output=make_edit_review(
                violations=(
                    make_judged_violation(
                        lines__start=2, lines__end=4, kinds=("code", "string-literal")
                    ),
                    make_judged_violation(lines__start=2, lines__end=2, kinds=("code",)),
                )
            )
        )

        result = ViolationsOnTriggers(("string-literal",), 0.9).evaluate(context)

        assert result == EvaluationReason(value=True)

    def test_violation_below_the_threshold_passes(
        self, make_evaluator_context, make_edit_review, make_judged_violation
    ):
        context = make_evaluator_context(
            output=make_edit_review(
                violations=(make_judged_violation(confidence=0.7, kinds=("number-literal",)),)
            )
        )

        result = ViolationsOnTriggers(("string-literal",), 0.9).evaluate(context)

        assert result == EvaluationReason(value=True)

    def test_binding_triggered_by_any_change_is_not_evaluated(
        self, make_evaluator_context, make_edit_review, make_judged_violation
    ):
        context = make_evaluator_context(
            output=make_edit_review(violations=(make_judged_violation(kinds=("code",)),))
        )

        result = ViolationsOnTriggers(("any",), 0.9).evaluate(context)

        assert result == {}

    def test_case_expected_valid_is_not_evaluated(
        self, make_evaluator_context, make_edit_review, make_judged_violation
    ):
        context = make_evaluator_context(
            expected_output=make_edit_review(outcome=Outcome.VALID),
            output=make_edit_review(violations=(make_judged_violation(kinds=("code",)),)),
        )

        result = ViolationsOnTriggers(("string-literal",), 0.9).evaluate(context)

        assert result == {}
