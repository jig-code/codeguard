import textwrap
from collections.abc import Iterator

import pytest
from pydantic import JsonValue, ValidationError

from codeguard.config import ChangeKind
from codeguard.repository import AddedRow, AllLines, KeptRow, RemovedRow, RowText, WorkingTree
from codeguard.review import JudgeRequest, Severity, Verdict
from codeguard.review.judge import INSTRUCTIONS, Confidence, Violation, output_schema
from codeguard.syntax import Classification

THRESHOLD = 0.9


class TestJudgeRequest:
    def test_prompt_holds_the_named_convention_then_the_changes(
        self, make_judge_rule, make_judge_request
    ):
        judge_rule = make_judge_rule(name="pricing", text="Prices are integers.\n")
        request = make_judge_request(
            judge_rule=judge_rule, file="pricing.py", changes="+     1\tA = 1\n"
        )

        assert request.prompt == (
            '<rule name="pricing">\nPrices are integers.\n</rule>\n\n'
            '<changes path="pricing.py">\n+     1\tA = 1\n</changes>\n'
        )

    def test_judged_lines_are_numbered_with_their_file_line_numbers(
        self, make_changed_lines, make_file_classification, tmp_path, make_binding, make_judge_rule
    ):
        returned = b"    return total - DISCOUNT"
        (tmp_path / "pricing.py").write_text(
            textwrap.dedent("""\
                DISCOUNT = 5


                def discounted(total):
                    return total - DISCOUNT
            """)
        )
        scope = make_changed_lines(
            file="pricing.py",
            rows=[
                KeptRow(1, 1),
                KeptRow(2, 2),
                KeptRow(3, 3),
                KeptRow(4, 4),
                AddedRow(5, RowText(returned)),
            ],
        )
        classified = make_file_classification(context_lines=frozenset({4, 5}))

        request = JudgeRequest.of_change(
            make_binding(),
            WorkingTree.at(tmp_path),
            "pricing.py",
            scope,
            Classification({"pricing.py": classified}),
        )

        assert request == JudgeRequest(
            make_judge_rule(),
            "pricing.py",
            "      4\tdef discounted(total):\n+     5\t    return total - DISCOUNT\n",
        )

    def test_removed_rows_come_before_the_line_after_them_with_their_reported_line(
        self, make_changed_lines, make_file_classification, tmp_path, make_binding, make_judge_rule
    ):
        (tmp_path / "pricing.py").write_text("DISCOUNT = 5\nTAX = 2\n")
        scope = make_changed_lines(
            file="pricing.py",
            rows=[KeptRow(1, 1), RemovedRow(2, RowText(b"FEE = 1")), KeptRow(3, 2)],
        )
        classified = make_file_classification(context_lines=frozenset({1, 2}))

        request = JudgeRequest.of_change(
            make_binding(),
            WorkingTree.at(tmp_path),
            "pricing.py",
            scope,
            Classification({"pricing.py": classified}),
        )

        assert request == JudgeRequest(
            make_judge_rule(),
            "pricing.py",
            "      1\tDISCOUNT = 5\n-     1\tFEE = 1\n      2\tTAX = 2\n",
        )

    def test_removed_row_that_is_not_utf_8_is_shown_replace_decoded(
        self, make_changed_lines, make_file_classification, tmp_path, make_binding, make_judge_rule
    ):
        (tmp_path / "pricing.py").write_text("DISCOUNT = 5\n")
        scope = make_changed_lines(
            file="pricing.py", rows=[KeptRow(1, 1), RemovedRow(2, RowText(b"FEE = '\xff'"))]
        )
        classified = make_file_classification(context_lines=frozenset({1}))

        request = JudgeRequest.of_change(
            make_binding(),
            WorkingTree.at(tmp_path),
            "pricing.py",
            scope,
            Classification({"pricing.py": classified}),
        )

        assert request == JudgeRequest(
            make_judge_rule(), "pricing.py", "      1\tDISCOUNT = 5\n-     1\tFEE = '\ufffd'\n"
        )

    def test_rows_removed_from_the_end_of_the_file_come_last(
        self, make_changed_lines, make_file_classification, tmp_path, make_binding, make_judge_rule
    ):
        (tmp_path / "pricing.py").write_text("DISCOUNT = 5\n")
        scope = make_changed_lines(
            file="pricing.py", rows=[KeptRow(1, 1), RemovedRow(2, RowText(b"TAX = 2"))]
        )
        classified = make_file_classification(context_lines=frozenset({1}))

        request = JudgeRequest.of_change(
            make_binding(),
            WorkingTree.at(tmp_path),
            "pricing.py",
            scope,
            Classification({"pricing.py": classified}),
        )

        assert request == JudgeRequest(
            make_judge_rule(), "pricing.py", "      1\tDISCOUNT = 5\n-     1\tTAX = 2\n"
        )

    def test_shown_lines_take_in_the_nodes_of_the_rule_triggers(
        self, make_changed_lines, make_file_classification, tmp_path, make_binding, make_judge_rule
    ):
        added = b"    x = 1"
        (tmp_path / "pricing.py").write_text(
            textwrap.dedent("""\
                try:
                    x = 1
                except:
                    pass
            """)
        )
        scope = make_changed_lines(
            file="pricing.py",
            rows=[KeptRow(1, 1), AddedRow(2, RowText(added)), KeptRow(2, 3), KeptRow(3, 4)],
        )
        classified = make_file_classification(
            context_lines=frozenset({2}),
            kind_lines={ChangeKind.CONTROL_FLOW: frozenset({1, 2, 3, 4})},
        )
        binding = make_binding(triggers=frozenset({ChangeKind.CONTROL_FLOW}))

        request = JudgeRequest.of_change(
            binding,
            WorkingTree.at(tmp_path),
            "pricing.py",
            scope,
            Classification({"pricing.py": classified}),
        )

        assert request == JudgeRequest(
            make_judge_rule(),
            "pricing.py",
            "      1\ttry:\n+     2\t    x = 1\n      3\texcept:\n      4\t    pass\n",
        )

    def test_all_lines_is_the_whole_file_changed(self, tmp_path, make_binding, make_judge_rule):
        (tmp_path / "pricing.py").write_text("DISCOUNT = 5\nTAX = 2")

        request = JudgeRequest.of_change(
            make_binding(),
            WorkingTree.at(tmp_path),
            "pricing.py",
            AllLines(("pricing.py",)),
            Classification(),
        )

        assert request == JudgeRequest(
            make_judge_rule(), "pricing.py", "+     1\tDISCOUNT = 5\n+     2\tTAX = 2\n"
        )

    def test_changed_point_past_the_end_of_the_file_is_left_out(
        self,
        make_new_file_changed_lines,
        make_file_classification,
        tmp_path,
        make_binding,
        make_judge_rule,
    ):
        (tmp_path / "pricing.py").write_text("DISCOUNT = 5\n")
        scope = make_new_file_changed_lines(
            file="pricing.py",
            content=textwrap.dedent("""\
                DISCOUNT = 5
                TAX = 2
            """).encode(),
        )
        classified = make_file_classification(context_lines=frozenset({1, 2}))

        request = JudgeRequest.of_change(
            make_binding(),
            WorkingTree.at(tmp_path),
            "pricing.py",
            scope,
            Classification({"pricing.py": classified}),
        )

        assert request == JudgeRequest(make_judge_rule(), "pricing.py", "+     1\tDISCOUNT = 5\n")

    def test_symlink_is_shown_as_its_link_text(
        self, make_new_file_changed_lines, tmp_path, make_binding, make_judge_rule
    ):
        (tmp_path / "rates.py").write_text("RATE = 2\n")
        link = "rates.py"
        (tmp_path / "pricing.py").symlink_to(link)
        scope = make_new_file_changed_lines(file="pricing.py", content=link.encode())

        request = JudgeRequest.of_change(
            make_binding(), WorkingTree.at(tmp_path), "pricing.py", scope, Classification()
        )

        assert request == JudgeRequest(make_judge_rule(), "pricing.py", "+     1\trates.py\n")

    def test_lines_are_numbered_as_git_numbers_them(
        self, make_changed_lines, make_file_classification, tmp_path, make_binding, make_judge_rule
    ):
        added = b"TAX = 2"
        (tmp_path / "pricing.py").write_bytes(b"DISCOUNT = 5\f\n" + added + b"\n")
        scope = make_changed_lines(
            file="pricing.py", rows=[KeptRow(1, 1), AddedRow(2, RowText(added))]
        )
        classified = make_file_classification(context_lines=frozenset({2}))

        request = JudgeRequest.of_change(
            make_binding(),
            WorkingTree.at(tmp_path),
            "pricing.py",
            scope,
            Classification({"pricing.py": classified}),
        )

        assert request == JudgeRequest(make_judge_rule(), "pricing.py", "+     2\tTAX = 2\n")

    def test_instructions_are_the_same_for_every_rule_and_file(
        self, make_judge_rule, make_judge_request
    ):
        request = make_judge_request(judge_rule=make_judge_rule(name="pricing"), file="pricing.py")

        assert request.instructions == INSTRUCTIONS


class TestViolation:
    @pytest.mark.parametrize("confidence", [0.85, 0.95, 1.1, 0.4])
    def test_confidence_off_the_scale_is_invalid(self, make_violation, confidence):
        with pytest.raises(ValidationError):
            make_violation(confidence=confidence)

    def test_schema_allows_only_the_scale(self):
        confidence = output_schema(Violation)["properties"]["confidence"]

        assert confidence["enum"] == [1.0, 0.9, 0.7, 0.5]

    def test_schema_describes_each_value_of_the_scale(self):
        description = output_schema(Violation)["properties"]["confidence"]["description"]

        described = [member.value for member in Confidence if f" {member.value}: " in description]
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

    def test_diagnostic_has_the_binding_rule_and_severity(
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


KEYWORDS_CLAUDE_CODE_ENFORCES_STRICTLY = frozenset(
    {
        "$schema",
        "type",
        "description",
        "title",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "enum",
        "const",
        "anyOf",
    }
)
KEYWORDS_CLAUDE_CODE_ENFORCES_STRICTLY_BESIDE_ANY_OF = frozenset(
    {"anyOf", "$schema", "description", "title"}
)


def subschemas(schema: dict[str, JsonValue]) -> Iterator[dict[str, JsonValue]]:
    yield schema
    children = [
        *(schema.get("properties") or {}).values(),
        *([schema["items"]] if "items" in schema else []),
        *(schema.get("anyOf") or []),
    ]
    for child in children:
        yield from subschemas(child)


class TestOutputSchema:
    def test_verdict_schema_uses_only_claude_codes_strict_keywords(self):
        schema = output_schema(Verdict)

        used = {keyword for subschema in subschemas(schema) for keyword in subschema}
        assert used - KEYWORDS_CLAUDE_CODE_ENFORCES_STRICTLY == set()

    def test_verdict_schema_has_nothing_but_a_description_beside_an_any_of(self):
        schema = output_schema(Verdict)

        beside = [
            set(subschema) - KEYWORDS_CLAUDE_CODE_ENFORCES_STRICTLY_BESIDE_ANY_OF
            for subschema in subschemas(schema)
            if "anyOf" in subschema
        ]
        assert [keywords for keywords in beside if keywords] == []

    def test_reference_is_inlined_with_its_own_description(self):
        schema = output_schema(Verdict)

        violation = schema["properties"]["violations"]["items"]
        assert violation["properties"]["lines"] == {
            "additionalProperties": False,
            "description": (
                "The first and last line of the code that breaks the rule, numbered as the "
                "`changes` element numbers them."
            ),
            "properties": {
                "start": {"description": "The first line.", "type": "integer"},
                "end": {
                    "description": "The last line: the same as `start` for one line.",
                    "type": "integer",
                },
            },
            "required": ["start", "end"],
            "title": "LineRange",
            "type": "object",
        }
