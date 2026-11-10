import pytest
import yaml

from codeguard.config import ConfigError
from codeguard.rule_tests import RuleEval, rule_evals


class TestRuleEvals:
    def test_eval_is_named_after_its_file(self, tmp_path, make_rule_eval_case):
        case = make_rule_eval_case()
        (tmp_path / "rule-evals").mkdir()
        (tmp_path / "rule-evals/enum-usage.yaml").write_text(
            yaml.safe_dump({"cases": [case.model_dump(mode="json", exclude_defaults=True)]})
        )

        evals = rule_evals(tmp_path)

        assert evals == [
            (tmp_path / "rule-evals/enum-usage.yaml", RuleEval(name="enum-usage", cases=(case,)))
        ]

    def test_eval_file_ending_in_yml_is_loaded(self, tmp_path, make_rule_eval_case):
        case = make_rule_eval_case()
        (tmp_path / "rule-evals").mkdir()
        (tmp_path / "rule-evals/enum-usage.yml").write_text(
            yaml.safe_dump({"cases": [case.model_dump(mode="json", exclude_defaults=True)]})
        )

        evals = rule_evals(tmp_path)

        assert evals == [
            (tmp_path / "rule-evals/enum-usage.yml", RuleEval(name="enum-usage", cases=(case,)))
        ]

    def test_two_eval_files_naming_one_rule_raise_a_config_error(
        self, tmp_path, make_rule_eval_case
    ):
        case = make_rule_eval_case().model_dump(mode="json", exclude_defaults=True)
        (tmp_path / "rule-evals").mkdir()
        (tmp_path / "rule-evals/enum-usage.yaml").write_text(yaml.safe_dump({"cases": [case]}))
        (tmp_path / "rule-evals/more.yaml").write_text(
            yaml.safe_dump({"name": "enum-usage", "cases": [case]})
        )

        with pytest.raises(ConfigError) as error:
            rule_evals(tmp_path)

        assert str(error.value) == (
            "a rule has one eval file; remove one of:\n"
            f"  {tmp_path}/rule-evals/enum-usage.yaml\n"
            f"  {tmp_path}/rule-evals/more.yaml"
        )

    def test_yaml_and_yml_eval_files_for_one_rule_raise_a_config_error(
        self, tmp_path, make_rule_eval_case
    ):
        case = make_rule_eval_case().model_dump(mode="json", exclude_defaults=True)
        (tmp_path / "rule-evals").mkdir()
        (tmp_path / "rule-evals/enum-usage.yaml").write_text(yaml.safe_dump({"cases": [case]}))
        (tmp_path / "rule-evals/enum-usage.yml").write_text(yaml.safe_dump({"cases": [case]}))

        with pytest.raises(ConfigError) as error:
            rule_evals(tmp_path)

        assert str(error.value) == (
            "a rule has one eval file; remove one of:\n"
            f"  {tmp_path}/rule-evals/enum-usage.yaml\n"
            f"  {tmp_path}/rule-evals/enum-usage.yml"
        )

    def test_codeguard_0_4_eval_file_raises_asking_to_convert_it(self, tmp_path):
        (tmp_path / "rule-evals").mkdir()
        (tmp_path / "rule-evals/enum-usage-eval.yml").write_text(
            yaml.safe_dump({"id": "enum-usage", "invalid": [{"after": "ship(status='shipped')\n"}]})
        )

        with pytest.raises(ConfigError) as error:
            rule_evals(tmp_path)

        assert str(error.value) == (
            f"{tmp_path}/rule-evals/enum-usage-eval.yml is a codeguard 0.4 rule eval; "
            "convert it to rule-evals/<rule id>.yaml"
        )

    @pytest.mark.parametrize(
        ("content", "error"),
        [
            pytest.param(
                {"cases": [{"name": "a string", "inputs": {"after": "x"}}]},
                "cases.0.expected_output: Field required",
                id="case-without-expected-output",
            ),
            pytest.param(
                {"cases": [{"inputs": {"after": "x"}, "expected_output": {"outcome": "valid"}}]},
                "cases.0.name: Field required",
                id="case-without-a-name",
            ),
            pytest.param(
                {
                    "cases": [
                        {
                            "name": "a string",
                            "inputs": {"after": "x"},
                            "expected_output": {"outcome": "valid"},
                        },
                        {
                            "name": "a string",
                            "inputs": {"after": "y"},
                            "expected_output": {"outcome": "valid"},
                        },
                    ]
                },
                "cases: Value error, cases share a name: a string",
                id="cases-sharing-a-name",
            ),
            pytest.param(
                {
                    "cases": [
                        {
                            "name": "a string",
                            "inputs": {"after": "x"},
                            "expected_output": {"outcome": "valid"},
                        }
                    ],
                    "evaluators": ["EqualsExpected"],
                },
                "evaluators: Extra inputs are not permitted",
                id="eval-declaring-evaluators",
            ),
            pytest.param(
                {
                    "cases": [
                        {
                            "name": "a string",
                            "inputs": {"after": "x"},
                            "expected_output": {"outcome": "uncertain"},
                        }
                    ]
                },
                "cases.0.expected_output: Value error, a case expects invalid, valid or "
                "skipped; one the judge can't decide isn't clear enough for a rule eval",
                id="case-expecting-uncertain",
            ),
            pytest.param(
                {
                    "cases": [
                        {
                            "name": "a string",
                            "inputs": {"after": "x"},
                            "expected_output": {"outcome": "invalid", "reason": "A string."},
                        }
                    ]
                },
                "cases.0.expected_output: Value error, a case expects no reason: the judge's "
                "reason is printed with the eval for whoever reads it, never checked",
                id="case-expecting-a-reason",
            ),
        ],
    )
    def test_malformed_eval_file_raises_a_config_error_naming_the_field(
        self, tmp_path, content, error
    ):
        (tmp_path / "rule-evals").mkdir()
        (tmp_path / "rule-evals/enum-usage.yaml").write_text(yaml.safe_dump(content))

        with pytest.raises(ConfigError) as raised:
            rule_evals(tmp_path)

        assert str(raised.value) == f"{tmp_path}/rule-evals/enum-usage.yaml is invalid:\n  {error}"


class TestEditReview:
    def test_listing_gives_a_violation_on_one_line_its_line(
        self, make_edit_review, make_judged_violation
    ):
        review = make_edit_review(
            reason="Judged.", violations=(make_judged_violation(line=2, end_line=2),)
        )

        assert review.listing == "\n  reason: Judged.\n  line 2 (0.90): Pass the member."

    def test_listing_gives_a_violation_over_several_lines_its_first_and_last_line(
        self, make_edit_review, make_judged_violation
    ):
        review = make_edit_review(
            reason="Judged.", violations=(make_judged_violation(line=2, end_line=4),)
        )

        assert review.listing == "\n  reason: Judged.\n  lines 2-4 (0.90): Pass the member."
