import pytest

from codeguard.config import RulesetLoader
from codeguard.rule_tests import MissingWhy, MissingWhyMode, RuleTestResult
from codeguard.rule_tests.missing_why import has_why_section, rules_without_why

RULE = "# Placement\n\nA method lives on the type whose data it reads.\n"
PATTERN_RULE = "id: no-print\nlanguage: python\nrule:\n  pattern: print($$$ARGS)\n"
RULE_BINDING = 'rule: placement\npaths: ["**/*.py"]\ntriggers: [any]\n'
NO_WHY_WARNING = "placement: no ## Why section in its rule file"


class TestHasWhySection:
    @pytest.mark.parametrize(
        "rule",
        [
            RULE,
            RULE + "\n## Why\n\n",
            RULE + "\n## Why\n## Examples\n\nship(Status.SHIPPED)\n",
        ],
        ids=["no-section", "empty-section", "section-without-text"],
    )
    def test_a_rule_without_a_why_text_has_no_why_section(self, rule):
        assert not has_why_section(rule)

    def test_a_why_section_with_text_is_a_why_section(self, make_judge_rule):
        assert has_why_section(make_judge_rule().text)

    def test_why_section_may_end_in_a_source(self, make_judge_rule):
        rule = make_judge_rule().text + "\nSource: https://example.com/style-guide#placement\n"

        assert has_why_section(rule)


class TestRulesWithoutWhy:
    def test_judge_rule_without_a_why_is_reported(self):
        assert rules_without_why({"placement": RULE}, ()) == (NO_WHY_WARNING,)

    def test_judge_rule_with_a_why_is_not_reported(self, make_judge_rule):
        assert rules_without_why({"placement": make_judge_rule().text}, ()) == ()

    def test_pattern_rule_without_a_why_is_reported(self):
        assert rules_without_why({}, ["no-print"]) == ("no-print: no metadata.why",)

    def test_judge_rules_come_first_sorted_by_id_then_pattern_rules(self):
        missing = rules_without_why({"placement": RULE, "naming": RULE}, ["no-print"])

        assert missing == (
            "naming: no ## Why section in its rule file",
            NO_WHY_WARNING,
            "no-print: no metadata.why",
        )


class TestMissingWhyMode:
    def test_warn_mode_reports_as_warnings(self):
        result = MissingWhyMode.WARN.result(("no-print: no metadata.why",))

        assert result == RuleTestResult(warnings=("no-print: no metadata.why",))

    def test_fail_mode_reports_as_problems_that_fail_the_run(self):
        result = MissingWhyMode.FAIL.result(("no-print: no metadata.why",))

        assert result == RuleTestResult(problems=("no-print: no metadata.why",))
        assert not result.passed

    def test_off_mode_reports_nothing(self):
        assert MissingWhyMode.OFF.result(("no-print: no metadata.why",)) == RuleTestResult()


class TestMissingWhy:
    def test_judge_rules_and_pattern_rules_of_a_ruleset_without_a_why_are_reported(self, directory):
        directory.write(".codeguard/rules/judge/placement.md", RULE)
        directory.write(".codeguard/bindings/placement.yaml", RULE_BINDING)
        directory.write(".codeguard/rules/pattern/no-print.yml", PATTERN_RULE)

        result = MissingWhy(RulesetLoader.local(directory.root)).run()

        assert result == RuleTestResult(warnings=(NO_WHY_WARNING, "no-print: no metadata.why"))

    def test_invalid_ruleset_reports_nothing(self, directory):
        directory.write(".codeguard/bindings/placement.yaml", RULE_BINDING)

        result = MissingWhy(RulesetLoader.local(directory.root)).run()

        assert result == RuleTestResult()
