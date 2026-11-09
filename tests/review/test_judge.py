import pytest
from git_repo import GitRepo
from pydantic import ValidationError

from codeguard.review import JudgeRequest, Severity, Verdict
from codeguard.review.judge import INSTRUCTIONS, Confidence, Violation, output_schema
from codeguard.working_tree import ChangedLines, WorkingTree

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

    def test_changes_are_the_diff_of_the_file_from_the_base(
        self, tmp_path, make_binding, make_skill
    ):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("pricing.py", "DISCOUNT = 5\n")
        git_repo.commit("Add pricing")
        git_repo.write("pricing.py", "DISCOUNT = 6\n")
        scope = WorkingTree(root=git_repo.root).changed_lines("HEAD")

        request = JudgeRequest.of_change(make_binding(), git_repo.root, "pricing.py", scope)

        assert request == JudgeRequest(
            make_skill(),
            "pricing.py",
            "diff --git a/pricing.py b/pricing.py\n"
            "index 1871a2f..bea06f6 100644\n"
            "--- a/pricing.py\n"
            "+++ b/pricing.py\n"
            "@@ -1 +1 @@\n"
            "-DISCOUNT = 5\n"
            "+DISCOUNT = 6\n",
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
