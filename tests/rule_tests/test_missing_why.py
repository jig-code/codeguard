import pytest
from rules_package import NO_PRINT_RULE, PLACEMENT_RULE

from codeguard.config import RulesetLoader
from codeguard.rule_tests import MissingWhy, MissingWhyMode, RuleTestResult

MISSING = ("naming: no ## Why section in its rule file", "no-breakpoint: no metadata.why")
NAMING_RULE = "# Naming\n\nA name says what a value is.\n"
NO_BREAKPOINT_RULE = "id: no-breakpoint\nlanguage: python\nrule:\n  pattern: breakpoint()\n"


class TestMissingWhyMode:
    @pytest.mark.parametrize(
        ("mode", "expected"),
        [
            (MissingWhyMode.WARN, RuleTestResult(warnings=MISSING)),
            (MissingWhyMode.FAIL, RuleTestResult(problems=MISSING)),
            (MissingWhyMode.OFF, RuleTestResult()),
        ],
        ids=["warn", "fail", "off"],
    )
    def test_mode_decides_how_the_missing_whys_are_reported(self, mode, expected):
        assert mode.result(MISSING) == expected

    def test_failing_report_fails_the_run(self):
        assert not MissingWhyMode.FAIL.result(MISSING).passed


class TestMissingWhy:
    def test_judge_rules_then_pattern_rules_without_a_why_are_reported(self, directory):
        directory.write(".codeguard/rules/judge/responsibility-placement.md", PLACEMENT_RULE)
        directory.write(".codeguard/rules/judge/naming.md", NAMING_RULE)
        directory.write(
            ".codeguard/bindings/responsibility-placement.yaml",
            'rule: responsibility-placement\npaths: ["**/*.py"]\ntriggers: [any]\n',
        )
        directory.write(
            ".codeguard/bindings/naming.yaml", 'rule: naming\npaths: ["**/*.py"]\ntriggers: [any]\n'
        )
        directory.write(".codeguard/rules/pattern/no-print.yml", NO_PRINT_RULE)
        directory.write(".codeguard/rules/pattern/no-breakpoint.yml", NO_BREAKPOINT_RULE)

        result = MissingWhy(RulesetLoader.local(directory.root)).run()

        assert result == RuleTestResult(warnings=MISSING)

    def test_invalid_ruleset_reports_nothing(self, directory):
        directory.write(
            ".codeguard/bindings/naming.yaml", 'rule: naming\npaths: ["**/*.py"]\ntriggers: [any]\n'
        )

        result = MissingWhy(RulesetLoader.local(directory.root)).run()

        assert result == RuleTestResult()
