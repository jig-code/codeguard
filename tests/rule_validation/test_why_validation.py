import pytest
import yaml
from rules_package import NO_PRINT_RULE_FILE

from codeguard.config import ConfigError, RulesetLoader
from codeguard.rule_validation import ValidationResult, WhyValidation, WhyValidationMode

MISSING = ("naming: no ## Why section in its rule file", "no-breakpoint: no metadata.why")
NO_WHY_RULE = "# A rule\n\nIt gives no reason.\n"
BINDING = {"paths": ["**/*.py"], "triggers": ["any"]}


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
    def test_legacy_skill_without_a_why_is_reported_before_pattern_rules(self, directory):
        directory.write("skills/naming/SKILL.md", f"---\nname: naming\n---\n{NO_WHY_RULE}")
        directory.write(
            ".codeguard/bindings/naming.yaml", yaml.safe_dump({"skill": "skills/naming"} | BINDING)
        )
        directory.write(
            ".codeguard/rules/pattern/a.yml",
            yaml.safe_dump({"id": "a-rule", "language": "python", "rule": {"pattern": "a()"}}),
        )

        result = WhyValidation(RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult(
            warnings=("naming: no ## Why section in its rule file", "a-rule: no metadata.why")
        )

    def test_pattern_rules_without_a_why_are_reported_by_id(self, directory):
        directory.write(".codeguard/rules/pattern/no-print.yml", NO_PRINT_RULE_FILE.read_text())
        directory.write(
            ".codeguard/rules/pattern/a.yml",
            yaml.safe_dump({"id": "z-rule", "language": "python", "rule": {"pattern": "z()"}}),
        )
        directory.write(
            ".codeguard/rules/pattern/b.yml",
            yaml.safe_dump({"id": "a-rule", "language": "python", "rule": {"pattern": "a()"}}),
        )

        result = WhyValidation(RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult(
            warnings=("a-rule: no metadata.why", "z-rule: no metadata.why")
        )

    def test_rule_file_bound_with_rule_is_left_to_the_format_validation(self, directory):
        directory.write(".codeguard/rules/judge/naming.md", NO_WHY_RULE)
        directory.write(
            ".codeguard/bindings/naming.yaml", yaml.safe_dump({"rule": "naming"} | BINDING)
        )

        result = WhyValidation(RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult()

    @pytest.mark.parametrize("mode", list(WhyValidationMode))
    def test_ruleset_that_does_not_load_reports_nothing(self, directory, mode):
        directory.write(
            ".codeguard/bindings/naming.yaml", yaml.safe_dump({"rule": "naming"} | BINDING)
        )

        result = WhyValidation(RulesetLoader.local(directory.root), mode).run()

        assert result == ValidationResult()

    @pytest.mark.parametrize("mode", list(WhyValidationMode))
    def test_pattern_rule_whose_why_is_not_text_is_a_config_error(self, directory, mode):
        directory.write(
            ".codeguard/rules/pattern/no-print.yml",
            yaml.safe_dump(
                {
                    "id": "no-print",
                    "language": "python",
                    "metadata": {"why": 1},
                    "rule": {"pattern": "print()"},
                }
            ),
        )

        with pytest.raises(ConfigError) as error:
            WhyValidation(RulesetLoader.local(directory.root), mode).run()

        assert str(error.value) == (
            f"{directory.root}/.codeguard is invalid:\n"
            "  rules.metadata.why: Input should be a valid string"
        )
