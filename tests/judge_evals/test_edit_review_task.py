from recording_judge import RecordingJudge, RecordingJudges

from codeguard.ast_grep import AstGrep
from codeguard.judge_evals import EditReviewTask
from codeguard.rule_tests import EditReview, Outcome
from codeguard.syntax import SyntaxScanner


class TestEditReviewTask:
    def test_file_outside_the_binding_paths_is_skipped_without_judging(
        self, make_binding, make_edit_case
    ):
        judges = RecordingJudges(RecordingJudge())
        task = EditReviewTask(
            make_binding(paths=("src/**/*.py",)), judges, 0.9, SyntaxScanner(AstGrep(), {})
        )

        review = task(make_edit_case(file="module.py"))

        assert review == EditReview(outcome=Outcome.SKIPPED)
        assert judges.created == []

    def test_change_outside_the_triggers_is_skipped_without_judging(
        self, make_binding, make_edit_case
    ):
        judges = RecordingJudges(RecordingJudge())
        task = EditReviewTask(
            make_binding(paths=("**/*.py",), triggers=frozenset({"string-literal"})),
            judges,
            0.9,
            SyntaxScanner(AstGrep(), {}),
        )

        review = task(make_edit_case(after="count = 1\n"))

        assert review == EditReview(outcome=Outcome.SKIPPED)
        assert judges.created == []

    def test_change_of_only_blank_lines_is_skipped_without_judging(
        self, make_binding, make_edit_case
    ):
        judges = RecordingJudges(RecordingJudge())
        task = EditReviewTask(
            make_binding(paths=("**/*.py",)), judges, 0.9, SyntaxScanner(AstGrep(), {})
        )

        review = task(
            make_edit_case(before="ship(status='shipped')\n", after="ship(status='shipped')\n\n\n")
        )

        assert review == EditReview(outcome=Outcome.SKIPPED)
        assert judges.created == []

    def test_violation_at_the_threshold_is_invalid_with_the_kinds_on_its_line(
        self, make_binding, make_edit_case, make_verdict, make_violation, make_judged_violation
    ):
        violation = make_violation(file="module.py", message="Pass the member.", confidence=0.9)
        task = EditReviewTask(
            make_binding(paths=("**/*.py",)),
            RecordingJudges(RecordingJudge(make_verdict(breaking=True, violations=(violation,)))),
            0.9,
            SyntaxScanner(AstGrep(), {}),
        )

        review = task(make_edit_case())

        assert review == EditReview(
            outcome=Outcome.INVALID,
            reason="The code breaks the convention.",
            violations=(
                make_judged_violation(kinds=("call", "code", "module-statement", "string-literal")),
            ),
        )

    def test_violation_below_the_threshold_is_uncertain(
        self, make_binding, make_edit_case, make_verdict, make_violation, make_judged_violation
    ):
        violation = make_violation(file="module.py", message="Pass the member.", confidence=0.7)
        task = EditReviewTask(
            make_binding(paths=("**/*.py",)),
            RecordingJudges(RecordingJudge(make_verdict(breaking=True, violations=(violation,)))),
            0.9,
            SyntaxScanner(AstGrep(), {}),
        )

        review = task(make_edit_case())

        assert review == EditReview(
            outcome=Outcome.UNCERTAIN,
            reason="The code breaks the convention.",
            violations=(
                make_judged_violation(
                    confidence=0.7, kinds=("call", "code", "module-statement", "string-literal")
                ),
            ),
        )

    def test_no_violation_is_valid_with_the_judge_reason(
        self, make_binding, make_edit_case, make_verdict
    ):
        task = EditReviewTask(
            make_binding(paths=("**/*.py",)),
            RecordingJudges(RecordingJudge(make_verdict())),
            0.9,
            SyntaxScanner(AstGrep(), {}),
        )

        review = task(make_edit_case())

        assert review == EditReview(outcome=Outcome.VALID, reason="The code keeps the convention.")

    def test_violation_on_an_unchanged_line_is_dropped(
        self, make_binding, make_edit_case, make_verdict, make_violation
    ):
        violation = make_violation(file="module.py", line=1, confidence=0.9)
        task = EditReviewTask(
            make_binding(paths=("**/*.py",)),
            RecordingJudges(RecordingJudge(make_verdict(breaking=True, violations=(violation,)))),
            0.9,
            SyntaxScanner(AstGrep(), {}),
        )

        review = task(
            make_edit_case(
                before="ship(status=Status.SHIPPED)\ncancel(status=Status.CANCELLED)\n",
                after="ship(status=Status.SHIPPED)\ncancel(status='cancelled')\n",
            )
        )

        assert review == EditReview(outcome=Outcome.VALID, reason="The code breaks the convention.")

    def test_violation_in_another_file_is_dropped(
        self, make_binding, make_edit_case, make_verdict, make_violation
    ):
        violation = make_violation(file="other.py", confidence=0.9)
        task = EditReviewTask(
            make_binding(paths=("**/*.py",)),
            RecordingJudges(RecordingJudge(make_verdict(breaking=True, violations=(violation,)))),
            0.9,
            SyntaxScanner(AstGrep(), {}),
        )

        review = task(make_edit_case())

        assert review == EditReview(outcome=Outcome.VALID, reason="The code breaks the convention.")
