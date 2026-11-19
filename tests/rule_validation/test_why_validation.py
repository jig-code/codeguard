import pytest
from rules_package import NO_PRINT_RULE, PLACEMENT_RULE

from codeguard.config import ConfigError, RulesetLoader
from codeguard.rule_validation import RuleTestResult, WhyValidation, WhyValidationMode

MISSING = ("naming: no ## Why section in its rule file", "no-breakpoint: no metadata.why")
NO_WHY_RULE = "# A rule\n\nIt gives no reason.\n"
BINDING = 'paths: ["**/*.py"]\ntriggers: [any]\n'


class TestWhyValidationMode:
    @pytest.mark.parametrize(
        ("mode", "expected"),
        [
            (WhyValidationMode.WARN, RuleTestResult(warnings=MISSING)),
            (WhyValidationMode.FAIL, RuleTestResult(problems=MISSING)),
            (WhyValidationMode.OFF, RuleTestResult()),
        ],
        ids=["warn", "fail", "off"],
    )
    def test_mode_decides_how_the_missing_whys_are_reported(self, mode, expected):
        assert mode.result(MISSING) == expected


class TestWhyValidation:
    def test_judge_rules_then_pattern_rules_without_a_why_are_reported_by_id(self, directory):
        directory.write(".codeguard/rules/judge/placement.md", PLACEMENT_RULE)
        directory.write(".codeguard/rules/judge/zebra.md", NO_WHY_RULE)
        directory.write(".codeguard/rules/judge/apple.md", NO_WHY_RULE)
        directory.write(".codeguard/bindings/a.yaml", f"rule: zebra\n{BINDING}")
        directory.write(".codeguard/bindings/b.yaml", f"rule: apple\n{BINDING}")
        directory.write(".codeguard/bindings/c.yaml", f"rule: placement\n{BINDING}")
        directory.write(".codeguard/rules/pattern/no-print.yml", NO_PRINT_RULE)
        directory.write(
            ".codeguard/rules/pattern/a.yml",
            "id: z-rule\nlanguage: python\nrule:\n  pattern: z()\n",
        )
        directory.write(
            ".codeguard/rules/pattern/b.yml",
            "id: a-rule\nlanguage: python\nrule:\n  pattern: a()\n",
        )

        result = WhyValidation(RulesetLoader.local(directory.root)).run()

        assert result == RuleTestResult(
            warnings=(
                "apple: no ## Why section in its rule file",
                "zebra: no ## Why section in its rule file",
                "a-rule: no metadata.why",
                "z-rule: no metadata.why",
            )
        )

    @pytest.mark.parametrize("mode", list(WhyValidationMode))
    def test_ruleset_that_does_not_load_reports_nothing(self, directory, mode):
        directory.write(".codeguard/bindings/naming.yaml", f"rule: naming\n{BINDING}")

        result = WhyValidation(RulesetLoader.local(directory.root), mode).run()

        assert result == RuleTestResult()

    @pytest.mark.parametrize("mode", list(WhyValidationMode))
    def test_pattern_rule_whose_why_is_not_text_is_a_config_error(self, directory, mode):
        directory.write(
            ".codeguard/rules/pattern/no-print.yml",
            "id: no-print\nlanguage: python\nmetadata:\n  why: 1\nrule:\n  pattern: print()\n",
        )

        with pytest.raises(ConfigError) as error:
            WhyValidation(RulesetLoader.local(directory.root), mode).run()

        assert str(error.value) == (
            f"{directory.root}/.codeguard is invalid:\n"
            "  rules.metadata.why: Input should be a valid string"
        )
