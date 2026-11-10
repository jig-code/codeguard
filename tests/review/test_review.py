import json
from io import StringIO

import pytest

from codeguard.review import ErrorType, Review, Severity


class TestReview:
    def test_error_diagnostic_blocks(self, make_diagnostic):
        result = Review(
            diagnostics=(make_diagnostic(warning=True), make_diagnostic(lines__start=2))
        )

        assert result.blocks is True

    def test_warning_diagnostic_does_not_block(self, make_diagnostic):
        result = Review(diagnostics=(make_diagnostic(warning=True),))

        assert result.blocks is False

    def test_write_lists_each_diagnostic(self, make_diagnostic):
        warning = make_diagnostic(warning=True)
        error = make_diagnostic(lines__start=2)
        out = StringIO()

        Review(diagnostics=(warning, error)).write(out)

        assert out.getvalue() == f"{warning}\n{error}\n"

    def test_write_json_prints_one_object(self, make_diagnostic):
        warning = make_diagnostic(warning=True)
        error = make_diagnostic(lines__start=2)
        out = StringIO()

        Review(diagnostics=(warning, error)).write_json(out)

        assert json.loads(out.getvalue()) == {"diagnostics": [warning.as_json(), error.as_json()]}

    @pytest.mark.parametrize("error_type", list(ErrorType))
    def test_judge_errors_as_warnings_turns_each_judge_error_into_a_warning(
        self, make_diagnostic, error_type
    ):
        review = Review(diagnostics=(make_diagnostic(judge_error=True, error_type=error_type),))

        assert review.with_judge_errors_as_warnings() == Review(
            diagnostics=(
                make_diagnostic(judge_error=True, error_type=error_type, severity=Severity.WARNING),
            )
        )

    def test_judge_errors_as_warnings_keeps_rule_violations(self, make_diagnostic):
        review = Review(
            diagnostics=(make_diagnostic(), make_diagnostic(judged=True, lines__start=2))
        )

        assert review.with_judge_errors_as_warnings() == review
