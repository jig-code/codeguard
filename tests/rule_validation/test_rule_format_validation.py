import pytest
from rules_package import PLACEMENT_RULE

from codeguard.config import RulesetLoader
from codeguard.rule_validation import RuleFormatValidation, ValidationResult

BINDING = 'paths: ["**/*.py"]\ntriggers: [any]\n'
LEGACY_SKILL = "---\nname: legacy\n---\n\n# Legacy\n\n## Notes\n"


def validate(directory, rule_file: str) -> ValidationResult:
    directory.write(".codeguard/rules/judge/naming.md", rule_file)
    directory.write(".codeguard/bindings/naming.yaml", f"rule: naming\n{BINDING}")
    return RuleFormatValidation(RulesetLoader.local(directory.root)).run()


class TestRuleFormatValidation:
    def test_title_statement_and_why_pass(self, directory):
        assert validate(directory, PLACEMENT_RULE) == ValidationResult()

    @pytest.mark.parametrize(
        "rule_file",
        [
            "# Naming\n\nA name says what it holds.\n",
            "# Naming\n\nA name says what it holds.\n\n## Why\n",
        ],
        ids=["no Why heading", "empty Why"],
    )
    def test_rule_without_a_why_is_a_problem(self, directory, rule_file):
        assert validate(directory, rule_file) == ValidationResult(
            problems=("naming: rule file has no `## Why` section with text",)
        )

    @pytest.mark.parametrize(
        "rule_file",
        [
            "A name says what it holds.\n",
            "---\nname: naming\n---\n\n# Naming\n\nA name says what it holds.\n",
            "",
        ],
        ids=["no title", "frontmatter", "empty file"],
    )
    def test_file_that_does_not_start_with_a_title_is_a_problem(self, directory, rule_file):
        assert validate(directory, rule_file) == ValidationResult(
            problems=("naming: rule file must start with a `# ` title",)
        )

    def test_title_with_no_statement_is_a_problem(self, directory):
        result = validate(directory, "# Naming\n\n## Why\n\nNames are read more than written.\n")

        assert result == ValidationResult(
            problems=("naming: rule file has no statement under its title",)
        )

    def test_section_other_than_why_is_a_problem(self, directory):
        rule_file = (
            "# Naming\n\nA name says what it holds.\n\n## Forms\n\nA list.\n\n"
            "## Why\n\nNames are read more than written.\n"
        )

        assert validate(directory, rule_file) == ValidationResult(
            problems=(
                "naming: rule file has the heading '## Forms', "
                "but holds only a title, the statement and `## Why`",
            )
        )

    def test_comment_in_a_code_fence_is_not_a_heading(self, directory):
        rule_file = (
            "# Naming\n\nA name says what it holds, as in:\n\n```\n# note\n```\n\n"
            "## Why\n\nNames are read more than written.\n"
        )

        assert validate(directory, rule_file) == ValidationResult()

    def test_rule_bound_with_the_legacy_skill_key_is_not_checked(self, directory):
        directory.write("skills/legacy/SKILL.md", LEGACY_SKILL)
        directory.write(".codeguard/bindings/legacy.yaml", f"skill: skills/legacy\n{BINDING}")

        result = RuleFormatValidation(RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult()

    def test_ruleset_that_does_not_load_reports_nothing(self, directory):
        directory.write(".codeguard/bindings/naming.yaml", f"rule: naming\n{BINDING}")

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
