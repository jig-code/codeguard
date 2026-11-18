import pytest

from codeguard.config import RulesetLoader
from codeguard.rule_tests import MissingWhy, MissingWhyMode, RuleTestResult
from codeguard.rule_tests.missing_why import has_why_section

RULE = "# Placement\n\nA method lives on the type whose data it reads.\n"
PATTERN_RULE = "id: no-print\nlanguage: python\nrule:\n  pattern: print($$$ARGS)\n"
RULE_BINDING = 'rule: placement\npaths: ["**/*.py"]\ntriggers: [any]\n'
SKILL_BINDING = 'skill: .codeguard/skills/placement\npaths: ["**/*.py"]\ntriggers: [any]\n'
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


class TestMissingWhy:
    def test_judge_rule_with_a_why_passes(self, git_repo, make_judge_rule):
        git_repo.write(".codeguard/rules/judge/placement.md", make_judge_rule().text)
        git_repo.write(".codeguard/bindings/placement.yaml", RULE_BINDING)

        result = MissingWhy(RulesetLoader.local(git_repo.root)).run()

        assert result == RuleTestResult()

    def test_judge_rule_without_a_why_warns(self, git_repo):
        git_repo.write(".codeguard/rules/judge/placement.md", RULE)
        git_repo.write(".codeguard/bindings/placement.yaml", RULE_BINDING)

        result = MissingWhy(RulesetLoader.local(git_repo.root)).run()

        assert result == RuleTestResult(warnings=(NO_WHY_WARNING,))

    def test_skill_directory_without_a_why_warns(self, git_repo):
        git_repo.write(".codeguard/skills/placement/SKILL.md", f"---\nname: placement\n---\n{RULE}")
        git_repo.write(".codeguard/bindings/placement.yaml", SKILL_BINDING)

        result = MissingWhy(RulesetLoader.local(git_repo.root)).run()

        assert result == RuleTestResult(warnings=(NO_WHY_WARNING,))

    def test_skill_directory_with_a_why_passes(self, git_repo, make_judge_rule):
        git_repo.write(
            ".codeguard/skills/placement/SKILL.md",
            f"---\nname: placement\n---\n{make_judge_rule().text}",
        )
        git_repo.write(".codeguard/bindings/placement.yaml", SKILL_BINDING)

        result = MissingWhy(RulesetLoader.local(git_repo.root)).run()

        assert result == RuleTestResult()

    def test_pattern_rule_with_a_why_passes(self, git_repo):
        git_repo.write(
            ".codeguard/rules/pattern/no-print.yml",
            PATTERN_RULE + "metadata:\n  why: Print skips the log levels.\n",
        )

        result = MissingWhy(RulesetLoader.local(git_repo.root)).run()

        assert result == RuleTestResult()

    @pytest.mark.parametrize(
        "metadata",
        ["", "metadata:\n  source: https://example.com\n", "metadata:\n  why: ''\n"],
        ids=["no-metadata", "source-only", "empty-why"],
    )
    def test_pattern_rule_without_a_why_warns(self, git_repo, metadata):
        git_repo.write(".codeguard/rules/pattern/no-print.yml", PATTERN_RULE + metadata)

        result = MissingWhy(RulesetLoader.local(git_repo.root)).run()

        assert result == RuleTestResult(warnings=("no-print: no metadata.why",))

    def test_fail_mode_fails_each_rule_without_a_why(self, git_repo):
        git_repo.write(".codeguard/rules/judge/placement.md", RULE)
        git_repo.write(".codeguard/bindings/placement.yaml", RULE_BINDING)
        git_repo.write(".codeguard/rules/pattern/no-print.yml", PATTERN_RULE)

        result = MissingWhy(RulesetLoader.local(git_repo.root), MissingWhyMode.FAIL).run()

        assert result == RuleTestResult(problems=(NO_WHY_WARNING, "no-print: no metadata.why"))
        assert not result.passed

    def test_off_mode_reports_nothing(self, git_repo):
        git_repo.write(".codeguard/rules/judge/placement.md", RULE)
        git_repo.write(".codeguard/bindings/placement.yaml", RULE_BINDING)

        result = MissingWhy(RulesetLoader.local(git_repo.root), MissingWhyMode.OFF).run()

        assert result == RuleTestResult()

    def test_a_gate_needs_no_why(self, git_repo):
        git_repo.write(
            ".codeguard/gates/enum-value.yml",
            "id: enum-value\nlanguage: python\nrule:\n  pattern: $X.value\n",
        )

        result = MissingWhy(RulesetLoader.local(git_repo.root)).run()

        assert result == RuleTestResult()
