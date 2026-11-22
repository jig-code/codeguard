import yaml
from rules_package import PLACEMENT_RULE

from codeguard.config import RulesetLoader
from codeguard.rule_validation import RuleFormatValidation, ValidationResult

BINDING = {"paths": ["**/*.py"], "triggers": ["any"]}
LEGACY_SKILL = "---\nname: legacy\n---\n\n# Legacy\n\n## Notes\n"


class TestRuleFormatValidation:
    def test_well_formed_rule_has_no_problems(self, directory):
        directory.write(".codeguard/rules/judge/placement.md", PLACEMENT_RULE)
        directory.write(
            ".codeguard/bindings/placement.yaml", yaml.safe_dump({"rule": "placement"} | BINDING)
        )

        result = RuleFormatValidation(RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult()

    def test_problem_is_reported_with_its_rule_id(self, directory):
        directory.write(".codeguard/rules/judge/naming.md", "no title\n")
        directory.write(
            ".codeguard/bindings/naming.yaml", yaml.safe_dump({"rule": "naming"} | BINDING)
        )

        result = RuleFormatValidation(RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult(
            problems=("naming: rule file must start with a `# ` title",)
        )

    def test_legacy_skill_is_not_checked(self, directory):
        directory.write("skills/legacy/SKILL.md", LEGACY_SKILL)
        directory.write(
            ".codeguard/bindings/legacy.yaml", yaml.safe_dump({"skill": "skills/legacy"} | BINDING)
        )

        result = RuleFormatValidation(RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult()

    def test_ruleset_that_does_not_load_reports_nothing(self, directory):
        directory.write(
            ".codeguard/bindings/naming.yaml", yaml.safe_dump({"rule": "naming"} | BINDING)
        )

        result = RuleFormatValidation(RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult()
