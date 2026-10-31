import pytest
from pydantic import ValidationError

from codeguard.review import JudgeRequest, Severity, Verdict
from codeguard.review.judge import INSTRUCTIONS, Violation
from codeguard.working_tree import AllLines, ChangedLines, Removal

THRESHOLD = 0.9


class TestJudgeRequest:
    def test_prompt_holds_the_named_convention_then_the_changes(
        self, make_skill, make_judge_request
    ):
        skill = make_skill(name="pricing", text="Prices are integers.\n")
        request = make_judge_request(skill=skill, file="pricing.py", changes="+     1\tA = 1\n")

        assert request.prompt == (
            '<convention name="pricing">\nPrices are integers.\n</convention>\n\n'
            '<changes path="pricing.py">\n+     1\tA = 1\n</changes>\n'
        )

    def test_convention_is_the_skill_and_the_supplement_for_the_file_language(
        self, tmp_path, make_binding, make_skill
    ):
        (tmp_path / "orders.py").write_text('STATUS = "shipped"\n')
        skill = make_skill()
        supplement = make_skill(text="## In Python\n\nA module constant is a home.\n")
        binding = make_binding(skill=skill, supplements={"python": supplement})
        scope = ChangedLines({"orders.py": frozenset({1})})

        request = JudgeRequest.of_change(binding, tmp_path, "orders.py", scope)

        assert request.skill.text == f"{skill.text}\n{supplement.text}"

    def test_judged_lines_are_numbered_with_their_file_line_numbers(
        self, tmp_path, make_binding, make_skill
    ):
        (tmp_path / "pricing.py").write_text(
            "DISCOUNT = 5\n\n\ndef discounted(total):\n    return total - DISCOUNT\n"
        )
        scope = ChangedLines({"pricing.py": frozenset({5})}).with_judged_lines(
            {"pricing.py": frozenset({4, 5})}
        )

        request = JudgeRequest.of_change(make_binding(), tmp_path, "pricing.py", scope)

        assert request == JudgeRequest(
            make_skill(),
            "pricing.py",
            "      4\tdef discounted(total):\n+     5\t    return total - DISCOUNT\n",
        )

    def test_removed_rows_come_before_the_line_after_them_with_their_reported_line(
        self, tmp_path, make_binding, make_skill
    ):
        (tmp_path / "pricing.py").write_text("DISCOUNT = 5\nTAX = 2\n")
        scope = ChangedLines(
            {},
            deletions={"pricing.py": frozenset({1})},
            removals={
                "pricing.py": (Removal(before=2, line=1, rows=("FEE = 1",), base_lines=(2,)),)
            },
        ).with_judged_lines({"pricing.py": frozenset({1, 2})})

        request = JudgeRequest.of_change(make_binding(), tmp_path, "pricing.py", scope)

        assert request == JudgeRequest(
            make_skill(),
            "pricing.py",
            "      1\tDISCOUNT = 5\n-     1\tFEE = 1\n      2\tTAX = 2\n",
        )

    def test_rows_removed_from_the_end_of_the_file_come_last(
        self, tmp_path, make_binding, make_skill
    ):
        (tmp_path / "pricing.py").write_text("DISCOUNT = 5\n")
        scope = ChangedLines(
            {},
            deletions={"pricing.py": frozenset({1})},
            removals={
                "pricing.py": (Removal(before=2, line=1, rows=("TAX = 2",), base_lines=(2,)),)
            },
        )

        request = JudgeRequest.of_change(make_binding(), tmp_path, "pricing.py", scope)

        assert request == JudgeRequest(
            make_skill(), "pricing.py", "      1\tDISCOUNT = 5\n-     1\tTAX = 2\n"
        )

    def test_shown_lines_take_in_the_nodes_of_the_rule_triggers(
        self, tmp_path, make_binding, make_skill
    ):
        (tmp_path / "pricing.py").write_text("try:\n    x = 1\nexcept:\n    pass\n")
        scope = (
            ChangedLines({"pricing.py": frozenset({2})})
            .with_judged_lines({"pricing.py": frozenset({2})})
            .with_kind_lines({"pricing.py": {"control-flow": frozenset({1, 2, 3, 4})}})
        )
        binding = make_binding(triggers=frozenset({"control-flow"}))

        request = JudgeRequest.of_change(binding, tmp_path, "pricing.py", scope)

        assert request == JudgeRequest(
            make_skill(),
            "pricing.py",
            "      1\ttry:\n+     2\t    x = 1\n      3\texcept:\n      4\t    pass\n",
        )

    def test_all_lines_is_the_whole_file_changed(self, tmp_path, make_binding, make_skill):
        (tmp_path / "pricing.py").write_text("DISCOUNT = 5\nTAX = 2")

        request = JudgeRequest.of_change(
            make_binding(), tmp_path, "pricing.py", AllLines(("pricing.py",))
        )

        assert request == JudgeRequest(
            make_skill(), "pricing.py", "+     1\tDISCOUNT = 5\n+     2\tTAX = 2\n"
        )

    def test_changed_point_past_the_end_of_the_file_is_left_out(
        self, tmp_path, make_binding, make_skill
    ):
        (tmp_path / "pricing.py").write_text("DISCOUNT = 5\n")
        scope = ChangedLines({"pricing.py": frozenset({1, 2})})

        request = JudgeRequest.of_change(make_binding(), tmp_path, "pricing.py", scope)

        assert request == JudgeRequest(make_skill(), "pricing.py", "+     1\tDISCOUNT = 5\n")

    def test_lines_are_numbered_as_git_numbers_them(self, tmp_path, make_binding, make_skill):
        (tmp_path / "pricing.py").write_text("DISCOUNT = 5\f\nTAX = 2\n")
        scope = ChangedLines({"pricing.py": frozenset({2})})

        request = JudgeRequest.of_change(make_binding(), tmp_path, "pricing.py", scope)

        assert request == JudgeRequest(make_skill(), "pricing.py", "+     2\tTAX = 2\n")

    def test_instructions_are_the_same_for_every_rule_and_file(
        self, make_skill, make_judge_request
    ):
        request = make_judge_request(skill=make_skill(name="pricing"), file="pricing.py")

        assert request.instructions == INSTRUCTIONS


class TestViolation:
    @pytest.mark.parametrize("confidence", [0.85, 0.95, 1.1, 0.4])
    def test_confidence_off_the_scale_is_invalid(self, make_violation, confidence):
        with pytest.raises(ValidationError):
            make_violation(confidence=confidence)

    def test_schema_allows_only_the_scale(self):
        schema = Violation.model_json_schema()

        assert schema["$defs"]["Confidence"]["enum"] == [1.0, 0.9, 0.7, 0.5]

    def test_note_is_invalid(self):
        with pytest.raises(ValidationError):
            Violation.model_validate(
                {
                    "file": "a.py",
                    "line": 1,
                    "message": "Move it.",
                    "note": "Fix it.",
                    "confidence": 1,
                }
            )


class TestVerdict:
    def test_unconfident_violation_shows_why_it_is_only_a_warning(
        self, make_violation, make_binding
    ):
        verdict = Verdict(violations=(make_violation(confidence=0.7),))

        [diagnostic] = verdict.diagnostics_for(make_binding(), "a.py", THRESHOLD)

        assert str(diagnostic).startswith(
            f"a.py:1: warning {make_binding().rule}: Use logging, not print. (confidence 0.70)"
        )

    def test_judged_diagnostic_prints_only_its_summary(self, make_violation, make_binding):
        verdict = Verdict(violations=(make_violation(),))

        [diagnostic] = verdict.diagnostics_for(make_binding(), "a.py", THRESHOLD)

        assert str(diagnostic) == (
            f"a.py:1: error {make_binding().rule}: Use logging, not print. (confidence 1.00) "
            f"[{diagnostic.id}]"
        )

    def test_diagnostic_has_the_binding_skill_and_severity(
        self, make_violation, make_binding, make_diagnostic
    ):
        verdict = Verdict(violations=(make_violation(),))

        diagnostics = verdict.diagnostics_for(
            make_binding(severity=Severity.WARNING), "a.py", THRESHOLD
        )

        assert diagnostics == (make_diagnostic(judged=True, severity=Severity.WARNING),)

    def test_violations_in_other_files_are_left_out(self, make_violation, make_binding):
        verdict = Verdict(violations=(make_violation(file="b.py"),))

        assert verdict.diagnostics_for(make_binding(), "a.py", THRESHOLD) == ()

    def test_error_at_the_threshold_stays_an_error(
        self, make_violation, make_binding, make_diagnostic
    ):
        verdict = Verdict(violations=(make_violation(confidence=THRESHOLD),))

        diagnostics = verdict.diagnostics_for(make_binding(), "a.py", THRESHOLD)

        assert diagnostics == (make_diagnostic(judged=True, confidence=THRESHOLD),)

    def test_error_below_the_threshold_is_a_warning(
        self, make_violation, make_binding, make_diagnostic
    ):
        verdict = Verdict(violations=(make_violation(confidence=0.5),))

        diagnostics = verdict.diagnostics_for(make_binding(), "a.py", THRESHOLD)

        assert diagnostics == (
            make_diagnostic(judged=True, severity=Severity.WARNING, confidence=0.5),
        )

    def test_info_below_the_threshold_stays_info(
        self, make_violation, make_binding, make_diagnostic
    ):
        verdict = Verdict(violations=(make_violation(confidence=0.5),))

        diagnostics = verdict.diagnostics_for(
            make_binding(severity=Severity.INFO), "a.py", THRESHOLD
        )

        assert diagnostics == (
            make_diagnostic(judged=True, severity=Severity.INFO, confidence=0.5),
        )
