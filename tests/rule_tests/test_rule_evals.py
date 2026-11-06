import pytest
import yaml

from codeguard.config import ConfigError
from codeguard.rule_tests import rule_evals


def a_case(name: str = "a string", outcome: str = "valid") -> dict[str, object]:
    return {
        "name": name,
        "inputs": {"after": "ship(status='shipped')\n"},
        "expected_output": {"outcome": outcome},
    }


class TestRuleEvals:
    def test_eval_is_named_after_its_file(self, tmp_path):
        (tmp_path / "rule-evals").mkdir()
        (tmp_path / "rule-evals/enum-usage.yaml").write_text(yaml.safe_dump({"cases": [a_case()]}))

        [(_, loaded)] = rule_evals(tmp_path)

        assert loaded.name == "enum-usage"

    def test_eval_file_ending_in_yml_is_loaded(self, tmp_path):
        (tmp_path / "rule-evals").mkdir()
        (tmp_path / "rule-evals/enum-usage.yml").write_text(yaml.safe_dump({"cases": [a_case()]}))

        [(file, _)] = rule_evals(tmp_path)

        assert file == tmp_path / "rule-evals/enum-usage.yml"

    def test_two_eval_files_naming_one_rule_raise_a_config_error(self, tmp_path):
        (tmp_path / "rule-evals").mkdir()
        (tmp_path / "rule-evals/enum-usage.yaml").write_text(yaml.safe_dump({"cases": [a_case()]}))
        (tmp_path / "rule-evals/more.yaml").write_text(
            yaml.safe_dump({"name": "enum-usage", "cases": [a_case()]})
        )

        with pytest.raises(ConfigError) as error:
            rule_evals(tmp_path)

        assert str(error.value) == (
            "a rule has one eval file; remove one of:\n"
            f"  {tmp_path}/rule-evals/enum-usage.yaml\n"
            f"  {tmp_path}/rule-evals/more.yaml"
        )

    def test_yaml_and_yml_eval_files_for_one_rule_raise_a_config_error(self, tmp_path):
        (tmp_path / "rule-evals").mkdir()
        (tmp_path / "rule-evals/enum-usage.yaml").write_text(yaml.safe_dump({"cases": [a_case()]}))
        (tmp_path / "rule-evals/enum-usage.yml").write_text(yaml.safe_dump({"cases": [a_case()]}))

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
                {"cases": [a_case(), a_case()]},
                "cases: Value error, cases share a name: a string",
                id="cases-sharing-a-name",
            ),
            pytest.param(
                {"cases": [a_case()], "evaluators": ["EqualsExpected"]},
                "evaluators: Extra inputs are not permitted",
                id="eval-declaring-evaluators",
            ),
            pytest.param(
                {"cases": [a_case(outcome="uncertain")]},
                "cases.0.expected_output: Value error, a case expects invalid, valid or "
                "skipped; one the judge can't decide isn't clear enough for a rule eval",
                id="case-expecting-uncertain",
            ),
            pytest.param(
                {
                    "cases": [
                        {
                            **a_case(),
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
