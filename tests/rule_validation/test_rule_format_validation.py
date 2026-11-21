from rules_package import PLACEMENT_RULE

from codeguard.config import RulesetLoader
from codeguard.rule_validation import RuleFormatValidation, ValidationResult

BINDING = 'paths: ["**/*.py"]\ntriggers: [any]\n'
LEGACY_SKILL = "---\nname: legacy\n---\n\n# Legacy\n\n## Notes\n"


class TestRuleFormatValidation:
    def test_well_formed_rule_has_no_problems(self, directory):
        directory.write(".codeguard/rules/judge/placement.md", PLACEMENT_RULE)
        directory.write(".codeguard/bindings/placement.yaml", f"rule: placement\n{BINDING}")

        result = RuleFormatValidation(RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult()

    def test_problems_are_reported_by_rule_id(self, directory):
        directory.write(".codeguard/rules/judge/zebra.md", "no title\n")
        directory.write(".codeguard/rules/judge/apple.md", "no title\n")
        directory.write(".codeguard/bindings/a.yaml", f"rule: zebra\n{BINDING}")
        directory.write(".codeguard/bindings/b.yaml", f"rule: apple\n{BINDING}")

        result = RuleFormatValidation(RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult(
            problems=(
                "apple: rule file must start with a `# ` title",
                "zebra: rule file must start with a `# ` title",
            )
        )

    def test_rule_bound_with_the_legacy_skill_key_is_not_checked(self, directory):
        directory.write("skills/legacy/SKILL.md", LEGACY_SKILL)
        directory.write(".codeguard/bindings/legacy.yaml", f"skill: skills/legacy\n{BINDING}")

        result = RuleFormatValidation(RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult()

    def test_ruleset_that_does_not_load_reports_nothing(self, directory):
        directory.write(".codeguard/bindings/naming.yaml", f"rule: naming\n{BINDING}")

        result = RuleFormatValidation(RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult()
