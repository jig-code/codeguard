import pytest
from rules_package import NO_PRINT_RULE, PLACEMENT_RULE

from codeguard.config import ConfigError, RulesetLoader
from codeguard.rule_validation import ValidationResult, WhyValidation, WhyValidationMode

MISSING = ("naming: no ## Why section in its rule file", "no-breakpoint: no metadata.why")
NO_WHY_RULE = "# A rule\n\nIt gives no reason.\n"
BINDING = 'paths: ["**/*.py"]\ntriggers: [any]\n'


class TestWhyValidationMode:
    @pytest.mark.parametrize(
        ("mode", "expected"),
        [
            (WhyValidationMode.WARN, ValidationResult(warnings=MISSING)),
            (WhyValidationMode.FAIL, ValidationResult(problems=MISSING)),
            (WhyValidationMode.OFF, ValidationResult()),
        ],
        ids=["warn", "fail", "off"],
    )
    def test_mode_decides_how_the_missing_whys_are_reported(self, mode, expected):
        assert mode.result(MISSING) == expected


class TestWhyValidation:
    def test_judge_rules_then_pattern_rules_without_a_why_are_reported_by_id(self, directory):
        directory.write("skills/placement/SKILL.md", PLACEMENT_RULE)
        directory.write("skills/zebra/SKILL.md", NO_WHY_RULE)
        directory.write("skills/apple/SKILL.md", NO_WHY_RULE)
        directory.write(".codeguard/bindings/a.yaml", f"skill: skills/zebra\n{BINDING}")
        directory.write(".codeguard/bindings/b.yaml", f"skill: skills/apple\n{BINDING}")
        directory.write(".codeguard/bindings/c.yaml", f"skill: skills/placement\n{BINDING}")
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

        assert result == ValidationResult(
            warnings=(
                "apple: no ## Why section in its rule file",
                "zebra: no ## Why section in its rule file",
                "a-rule: no metadata.why",
                "z-rule: no metadata.why",
            )
        )

    def test_rule_file_bound_with_rule_is_left_to_the_format_validation(self, directory):
        directory.write(".codeguard/rules/judge/naming.md", NO_WHY_RULE)
        directory.write(".codeguard/bindings/naming.yaml", f"rule: naming\n{BINDING}")

        result = WhyValidation(RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult()

    @pytest.mark.parametrize("mode", list(WhyValidationMode))
    def test_ruleset_that_does_not_load_reports_nothing(self, directory, mode):
        directory.write(".codeguard/bindings/naming.yaml", f"rule: naming\n{BINDING}")

        result = WhyValidation(RulesetLoader.local(directory.root), mode).run()

        assert result == ValidationResult()

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
