import pytest
from pydantic import ValidationError

from codeguard.review import ErrorType, Severity


class TestDiagnostic:
    def test_id_ignores_message_severity_and_note(self, make_diagnostic):
        diagnostic = make_diagnostic()
        reworded = make_diagnostic(
            message="Reworded.", severity=Severity.WARNING, note="Call logger.info instead."
        )

        assert diagnostic.id == reworded.id

    def test_id_differs_by_first_line(self, make_diagnostic):
        diagnostic = make_diagnostic(lines__start=2, lines__end=4)
        moved = make_diagnostic(lines__start=3, lines__end=4)

        assert diagnostic.id != moved.id

    def test_id_differs_by_last_line(self, make_diagnostic):
        diagnostic = make_diagnostic(lines__start=2, lines__end=4)
        longer = make_diagnostic(lines__start=2, lines__end=5)

        assert diagnostic.id != longer.id

    def test_str_gives_a_violation_over_several_lines_its_first_and_last_line(
        self, make_diagnostic
    ):
        diagnostic = make_diagnostic(lines__start=2, lines__end=4, note=None)

        assert str(diagnostic) == (
            f"a.py:2-4: error no-print: Use logging, not print. [{diagnostic.id}]"
        )

    def test_str_indents_note_under_summary(self, make_diagnostic):
        diagnostic = make_diagnostic()

        assert str(diagnostic) == (
            f"a.py:1: error no-print: Use logging, not print. [{diagnostic.id}]\n"
            "  print bypasses log levels.\n"
            "  Call logger.info instead."
        )

    def test_str_without_a_line_names_only_the_file(self, make_diagnostic):
        diagnostic = make_diagnostic(warning=True, lines=None)

        assert str(diagnostic) == (
            f"a.py: warning no-breakpoint: Remove breakpoint(). [{diagnostic.id}]"
        )

    def test_str_without_note_is_summary_only(self, make_diagnostic):
        diagnostic = make_diagnostic(warning=True)

        assert str(diagnostic) == (
            f"a.py:1: warning no-breakpoint: Remove breakpoint(). [{diagnostic.id}]"
        )

    def test_judge_error_without_an_error_type_is_invalid(self, make_diagnostic):
        with pytest.raises(ValidationError):
            make_diagnostic(judge_error=True, error_type=None)

    def test_error_type_on_a_finding_is_invalid(self, make_diagnostic):
        with pytest.raises(ValidationError):
            make_diagnostic(judged=True, error_type=ErrorType.TIMEOUT)

    def test_as_warning_keeps_everything_but_the_severity(self, make_diagnostic):
        diagnostic = make_diagnostic(judge_error=True)

        assert diagnostic.as_warning() == make_diagnostic(
            judge_error=True, severity=Severity.WARNING
        )

    def test_json_has_every_field_and_no_judged_note(self, make_diagnostic):
        diagnostic = make_diagnostic(judged=True, confidence=0.95)

        assert diagnostic.as_json() == {
            "id": diagnostic.id,
            "rule": diagnostic.rule,
            "file": "a.py",
            "lines": {"start": 1, "end": 1},
            "message": "Use logging, not print.",
            "severity": "error",
            "category": "judged",
            "confidence": 0.95,
            "error_type": None,
            "note": None,
            "blocks": True,
        }

    def test_judge_error_json_has_its_error_type(self, make_diagnostic):
        diagnostic = make_diagnostic(judge_error=True, error_type=ErrorType.TIMEOUT)

        assert diagnostic.as_json()["error_type"] == "timeout"

    def test_pattern_json_keeps_its_note(self, make_diagnostic):
        diagnostic = make_diagnostic()

        assert diagnostic.as_json()["note"] == diagnostic.note
