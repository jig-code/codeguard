import yaml

from codeguard.config import RulesetLoader
from codeguard.judge_evals import EvalCoverage, EvalSelection
from codeguard.rule_validation import ValidationResult

ENUM_RULE = "# Enum usage\n\nPass the enum member, never a bare literal.\n"
ENUM_BINDING = {"rule": "enum-usage", "paths": ["**/*.py"], "triggers": ["any"]}
INVALID_CASE = {
    "name": "a literal",
    "inputs": {"after": "ship('shipped')\n"},
    "expected_output": {"outcome": "invalid"},
}


class TestEvalCoverage:
    def test_judge_rule_without_an_invalid_case_fails(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", yaml.safe_dump(ENUM_BINDING))
        result = EvalCoverage(RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult(problems=("enum-usage: no eval with an invalid case",))

    def test_judge_rule_with_an_invalid_case_passes(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", yaml.safe_dump(ENUM_BINDING))
        directory.write(
            ".codeguard/rule-evals/enum-usage.yaml", yaml.safe_dump({"cases": [INVALID_CASE]})
        )

        assert EvalCoverage(RulesetLoader.local(directory.root)).run() == ValidationResult()

    def test_judge_rule_with_only_a_valid_case_fails(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", yaml.safe_dump(ENUM_BINDING))
        directory.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump(
                {
                    "cases": [
                        {
                            "name": "a literal",
                            "inputs": {"after": "ship(Status.SHIPPED)\n"},
                            "expected_output": {"outcome": "valid"},
                        }
                    ]
                }
            ),
        )

        result = EvalCoverage(RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult(problems=("enum-usage: no eval with an invalid case",))

    def test_judge_rule_not_selected_is_not_checked(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", yaml.safe_dump(ENUM_BINDING))
        selection = EvalSelection(rules=frozenset({"other-rule"}))

        assert (
            EvalCoverage(RulesetLoader.local(directory.root), selection).run() == ValidationResult()
        )

    def test_selected_judge_rule_without_an_invalid_case_fails(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", yaml.safe_dump(ENUM_BINDING))
        selection = EvalSelection(rules=frozenset({"enum-usage"}))

        result = EvalCoverage(RulesetLoader.local(directory.root), selection).run()

        assert result == ValidationResult(problems=("enum-usage: no eval with an invalid case",))
