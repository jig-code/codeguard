from codeguard.config import RulesetLoader
from codeguard.judge_evals import EvalCoverage, EvalSelection
from codeguard.rule_tests import RuleTestResult

ENUM_RULE = "# Enum usage\n\nPass the enum member, never a bare literal.\n"
ENUM_BINDING = 'rule: enum-usage\npaths: ["**/*.py"]\ntriggers: [any]\n'
INVALID_EVAL = """\
cases:
  - name: a literal
    inputs:
      after: |
        ship('shipped')
    expected_output:
      outcome: invalid
"""


class TestEvalCoverage:
    def test_judge_rule_without_an_invalid_case_fails(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        result = EvalCoverage(RulesetLoader.local(directory.root)).run()

        assert result == RuleTestResult(problems=("enum-usage: no eval with an invalid case",))

    def test_judge_rule_with_an_invalid_case_passes(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(".codeguard/rule-evals/enum-usage.yaml", INVALID_EVAL)

        assert EvalCoverage(RulesetLoader.local(directory.root)).run() == RuleTestResult()

    def test_judge_rule_with_only_a_valid_case_fails(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            INVALID_EVAL.replace("ship('shipped')", "ship(Status.SHIPPED)").replace(
                "invalid", "valid"
            ),
        )

        result = EvalCoverage(RulesetLoader.local(directory.root)).run()

        assert result == RuleTestResult(problems=("enum-usage: no eval with an invalid case",))

    def test_judge_rule_not_selected_is_not_checked(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        selection = EvalSelection(rules=frozenset({"other-rule"}))

        assert (
            EvalCoverage(RulesetLoader.local(directory.root), selection).run() == RuleTestResult()
        )

    def test_selected_judge_rule_without_an_invalid_case_fails(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        selection = EvalSelection(rules=frozenset({"enum-usage"}))

        result = EvalCoverage(RulesetLoader.local(directory.root), selection).run()

        assert result == RuleTestResult(problems=("enum-usage: no eval with an invalid case",))
