import textwrap

import pytest
from pydantic import ValidationError

from codeguard.repository import AddedRow, AllLines, KeptRow, RemovedRow, RowText, WorkingTree
from codeguard.review import JudgeRequest, Severity, Verdict
from codeguard.review.judge import INSTRUCTIONS, Confidence, Violation, output_schema
from codeguard.syntax import Classification

THRESHOLD = 0.9


class TestJudgeRequest:
    def test_prompt_holds_the_named_convention_then_the_changes(
        self, make_skill, make_judge_request
    ):
        skill = make_skill(name="pricing", text="Prices are integers.\n")
        request = make_judge_request(
            skill=skill, file="pricing.py", changes="@@ -0,0 +1 @@\n+A = 1\n"
        )

        assert request.prompt == (
            '<rule name="pricing">\nPrices are integers.\n</rule>\n\n'
            '<changes path="pricing.py">\n@@ -0,0 +1 @@\n+A = 1\n</changes>\n'
        )

    def test_hunk_takes_in_the_context_lines_beyond_the_plain_context(
        self, make_changed_lines, make_file_classification, tmp_path, make_binding, make_skill
    ):
        returned = b"    return total - discount"
        (tmp_path / "pricing.py").write_text(
            textwrap.dedent("""\
                def discounted(total):
                    rate = 5
                    base = 100
                    floor = 0
                    discount = rate * base + floor
                    return total - discount
            """)
        )
        scope = make_changed_lines(
            file="pricing.py",
            rows=[
                KeptRow(1, 1),
                KeptRow(2, 2),
                KeptRow(3, 3),
                KeptRow(4, 4),
                KeptRow(5, 5),
                AddedRow(6, RowText(returned)),
            ],
        )
        classified = make_file_classification(context_lines=frozenset({1, 2, 3, 4, 5, 6}))

        request = JudgeRequest.of_change(
            make_binding(),
            WorkingTree.at(tmp_path),
            "pricing.py",
            scope,
            Classification({"pricing.py": classified}),
        )

        assert request == JudgeRequest(
            make_skill(),
            "pricing.py",
            textwrap.dedent("""\
                --- a/pricing.py
                +++ b/pricing.py
                @@ -1,5 +1,6 @@
                 def discounted(total):
                     rate = 5
                     base = 100
                     floor = 0
                     discount = rate * base + floor
                +    return total - discount
            """),
        )

    def test_changes_without_context_lines_get_three_lines_around_each_in_its_own_hunk(
        self, make_changed_lines, tmp_path, make_binding, make_skill
    ):
        (tmp_path / "pricing.py").write_text("".join(f"X{i} = {i}\n" for i in range(1, 11)))
        scope = make_changed_lines(
            file="pricing.py",
            rows=[
                RemovedRow(1, RowText(b"X1 = 0")),
                AddedRow(1, RowText(b"X1 = 1")),
                *(KeptRow(line, line) for line in range(2, 10)),
                RemovedRow(10, RowText(b"X10 = 0")),
                AddedRow(10, RowText(b"X10 = 10")),
            ],
        )

        request = JudgeRequest.of_change(
            make_binding(), WorkingTree.at(tmp_path), "pricing.py", scope, Classification()
        )

        assert request == JudgeRequest(
            make_skill(),
            "pricing.py",
            textwrap.dedent("""\
                --- a/pricing.py
                +++ b/pricing.py
                @@ -1,4 +1,4 @@
                -X1 = 0
                +X1 = 1
                 X2 = 2
                 X3 = 3
                 X4 = 4
                @@ -7,4 +7,4 @@
                 X7 = 7
                 X8 = 8
                 X9 = 9
                -X10 = 0
                +X10 = 10
            """),
        )

    def test_removed_row_falls_between_the_lines_around_it(
        self, make_changed_lines, tmp_path, make_binding, make_skill
    ):
        (tmp_path / "pricing.py").write_text("DISCOUNT = 5\nTAX = 2\n")
        scope = make_changed_lines(
            file="pricing.py",
            rows=[KeptRow(1, 1), RemovedRow(2, RowText(b"FEE = 1")), KeptRow(3, 2)],
        )

        request = JudgeRequest.of_change(
            make_binding(), WorkingTree.at(tmp_path), "pricing.py", scope, Classification()
        )

        assert request == JudgeRequest(
            make_skill(),
            "pricing.py",
            textwrap.dedent("""\
                --- a/pricing.py
                +++ b/pricing.py
                @@ -1,3 +1,2 @@
                 DISCOUNT = 5
                -FEE = 1
                 TAX = 2
            """),
        )

    def test_removed_row_that_is_not_utf_8_is_shown_replace_decoded(
        self, make_changed_lines, tmp_path, make_binding, make_skill
    ):
        (tmp_path / "pricing.py").write_text("DISCOUNT = 5\n")
        scope = make_changed_lines(
            file="pricing.py", rows=[KeptRow(1, 1), RemovedRow(2, RowText(b"FEE = '\xff'"))]
        )

        request = JudgeRequest.of_change(
            make_binding(), WorkingTree.at(tmp_path), "pricing.py", scope, Classification()
        )

        assert request == JudgeRequest(
            make_skill(),
            "pricing.py",
            "--- a/pricing.py\n+++ b/pricing.py\n@@ -1,2 +1 @@\n DISCOUNT = 5\n-FEE = '�'\n",
        )

    def test_renamed_file_is_shown_from_its_base_path(
        self, make_changed_lines, tmp_path, make_binding, make_skill
    ):
        (tmp_path / "pricing.py").write_text("TAX = 2\n")
        scope = make_changed_lines(
            file="pricing.py",
            base_path="rates.py",
            rows=[RemovedRow(1, RowText(b"TAX = 1")), AddedRow(1, RowText(b"TAX = 2"))],
        )

        request = JudgeRequest.of_change(
            make_binding(), WorkingTree.at(tmp_path), "pricing.py", scope, Classification()
        )

        assert request == JudgeRequest(
            make_skill(),
            "pricing.py",
            "--- a/rates.py\n+++ b/pricing.py\n@@ -1 +1 @@\n-TAX = 1\n+TAX = 2\n",
        )

    def test_all_lines_is_the_whole_file_added(self, tmp_path, make_binding, make_skill):
        (tmp_path / "pricing.py").write_text("DISCOUNT = 5\nTAX = 2")

        request = JudgeRequest.of_change(
            make_binding(),
            WorkingTree.at(tmp_path),
            "pricing.py",
            AllLines(("pricing.py",)),
            Classification(),
        )

        assert request == JudgeRequest(
            make_skill(),
            "pricing.py",
            textwrap.dedent("""\
                --- /dev/null
                +++ b/pricing.py
                @@ -0,0 +1,2 @@
                +DISCOUNT = 5
                +TAX = 2
            """),
        )

    def test_symlink_is_shown_as_its_link_text(
        self, make_new_file_changed_lines, tmp_path, make_binding, make_skill
    ):
        (tmp_path / "rates.py").write_text("RATE = 2\n")
        link = "rates.py"
        (tmp_path / "pricing.py").symlink_to(link)
        scope = make_new_file_changed_lines(file="pricing.py", content=link.encode())

        request = JudgeRequest.of_change(
            make_binding(), WorkingTree.at(tmp_path), "pricing.py", scope, Classification()
        )

        assert request == JudgeRequest(
            make_skill(),
            "pricing.py",
            "--- /dev/null\n+++ b/pricing.py\n@@ -0,0 +1 @@\n+rates.py\n",
        )

    def test_kept_line_ends_only_at_a_newline(
        self, make_changed_lines, tmp_path, make_binding, make_skill
    ):
        added = b"TAX = 2"
        (tmp_path / "pricing.py").write_bytes(b"DISCOUNT = 5\f\n" + added + b"\n")
        scope = make_changed_lines(
            file="pricing.py", rows=[KeptRow(1, 1), AddedRow(2, RowText(added))]
        )

        request = JudgeRequest.of_change(
            make_binding(), WorkingTree.at(tmp_path), "pricing.py", scope, Classification()
        )

        assert request == JudgeRequest(
            make_skill(),
            "pricing.py",
            "--- a/pricing.py\n+++ b/pricing.py\n@@ -1 +1,2 @@\n DISCOUNT = 5\f\n+TAX = 2\n",
        )

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
        schema = output_schema(Violation)

        options = schema["$defs"]["Confidence"]["anyOf"]
        assert [option["const"] for option in options] == [1.0, 0.9, 0.7, 0.5]

    def test_schema_describes_each_value_of_the_scale(self):
        schema = output_schema(Violation)

        options = schema["$defs"]["Confidence"]["anyOf"]
        described = [option["const"] for option in options if option.get("description")]
        assert described == [member.value for member in Confidence]

    def test_note_is_invalid(self):
        with pytest.raises(ValidationError):
            Violation.model_validate(
                {
                    "file": "a.py",
                    "lines": {"start": 1, "end": 1},
                    "message": "Move it.",
                    "note": "Fix it.",
                    "confidence": 1,
                }
            )


class TestVerdict:
    def test_unconfident_violation_shows_why_it_is_only_a_warning(
        self, make_violation, make_binding
    ):
        verdict = Verdict(
            reason="The code breaks the convention.", violations=(make_violation(confidence=0.7),)
        )

        [diagnostic] = verdict.diagnostics_for(make_binding(), "a.py", THRESHOLD)

        assert str(diagnostic).startswith(
            f"a.py:1: warning {make_binding().rule}: Use logging, not print. (confidence 0.70)"
        )

    def test_judged_diagnostic_prints_only_its_summary(self, make_violation, make_binding):
        verdict = Verdict(reason="The code breaks the convention.", violations=(make_violation(),))

        [diagnostic] = verdict.diagnostics_for(make_binding(), "a.py", THRESHOLD)

        assert str(diagnostic) == (
            f"a.py:1: error {make_binding().rule}: Use logging, not print. (confidence 1.00) "
            f"[{diagnostic.id}]"
        )

    def test_diagnostic_has_the_binding_skill_and_severity(
        self, make_violation, make_binding, make_diagnostic
    ):
        verdict = Verdict(reason="The code breaks the convention.", violations=(make_violation(),))

        diagnostics = verdict.diagnostics_for(
            make_binding(severity=Severity.WARNING), "a.py", THRESHOLD
        )

        assert diagnostics == (make_diagnostic(judged=True, severity=Severity.WARNING),)

    def test_violations_in_other_files_are_left_out(self, make_violation, make_binding):
        verdict = Verdict(
            reason="The code breaks the convention.", violations=(make_violation(file="b.py"),)
        )

        assert verdict.diagnostics_for(make_binding(), "a.py", THRESHOLD) == ()

    def test_error_at_the_threshold_stays_an_error(
        self, make_violation, make_binding, make_diagnostic
    ):
        verdict = Verdict(
            reason="The code breaks the convention.",
            violations=(make_violation(confidence=THRESHOLD),),
        )

        diagnostics = verdict.diagnostics_for(make_binding(), "a.py", THRESHOLD)

        assert diagnostics == (make_diagnostic(judged=True, confidence=THRESHOLD),)

    def test_error_below_the_threshold_is_a_warning(
        self, make_violation, make_binding, make_diagnostic
    ):
        verdict = Verdict(
            reason="The code breaks the convention.", violations=(make_violation(confidence=0.5),)
        )

        diagnostics = verdict.diagnostics_for(make_binding(), "a.py", THRESHOLD)

        assert diagnostics == (
            make_diagnostic(judged=True, severity=Severity.WARNING, confidence=0.5),
        )

    def test_info_below_the_threshold_stays_info(
        self, make_violation, make_binding, make_diagnostic
    ):
        verdict = Verdict(
            reason="The code breaks the convention.", violations=(make_violation(confidence=0.5),)
        )

        diagnostics = verdict.diagnostics_for(
            make_binding(severity=Severity.INFO), "a.py", THRESHOLD
        )

        assert diagnostics == (
            make_diagnostic(judged=True, severity=Severity.INFO, confidence=0.5),
        )
