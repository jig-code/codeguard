import pytest

from codeguard.config import RulesetLoader
from codeguard.rule_tests import MissingWhy, MissingWhyMode, RuleTestResult

RULE = "# Placement\n\nA method lives on the type whose data it reads.\n"
WHY = "\n## Why\n\nLogic away from its data is missed when the data changes.\n"
PATTERN_RULE = "id: no-print\nlanguage: python\nrule:\n  pattern: print($$$ARGS)\n"


@pytest.fixture
def judge_rule(repo):
    """The repo fixture's pattern rules, which have a why, plus a judge rule."""

    def write(rule: str) -> None:
        repo.write(".codeguard/rules/judge/placement.md", rule)
        repo.write(
            ".codeguard/bindings/placement.yaml",
            'rule: placement\npaths: ["**/*.py"]\ntriggers: [any]\n',
        )

    return write


def check(repo, mode: MissingWhyMode = MissingWhyMode.WARN) -> RuleTestResult:
    return MissingWhy(RulesetLoader.local(repo.root), mode).run()


class TestMissingWhy:
    def test_rules_that_say_why_pass(self, repo, judge_rule):
        judge_rule(RULE + WHY)

        assert check(repo) == RuleTestResult()

    @pytest.mark.parametrize(
        "rule",
        [RULE, RULE + "\n## Why\n\n", RULE + "\n## Why\n## Examples\n\nship(Status.SHIPPED)\n"],
        ids=["no-section", "empty-section", "section-without-text"],
    )
    def test_judge_rule_without_a_why_warns(self, repo, judge_rule, rule):
        judge_rule(rule)

        assert check(repo) == RuleTestResult(
            warnings=("placement: no ## Why section in rules/judge/placement.md",)
        )

    def test_why_section_may_end_in_a_source(self, repo, judge_rule):
        judge_rule(RULE + WHY + "\nSource: https://example.com/style-guide#placement\n")

        assert check(repo) == RuleTestResult()

    @pytest.mark.parametrize(
        "metadata",
        ["", "metadata:\n  source: https://example.com\n", "metadata:\n  why: ''\n"],
        ids=["no-metadata", "source-only", "empty-why"],
    )
    def test_pattern_rule_without_a_why_warns(self, repo, metadata):
        repo.write(".codeguard/rules/pattern/no-print.yml", PATTERN_RULE + metadata)

        assert check(repo) == RuleTestResult(warnings=("no-print: no metadata.why",))

    def test_fail_mode_fails_each_rule_without_a_why(self, repo, judge_rule):
        judge_rule(RULE)
        repo.write(".codeguard/rules/pattern/no-print.yml", PATTERN_RULE)

        result = check(repo, MissingWhyMode.FAIL)

        assert result == RuleTestResult(
            problems=(
                "placement: no ## Why section in rules/judge/placement.md",
                "no-print: no metadata.why",
            )
        )
        assert not result.passed

    def test_off_mode_reports_nothing(self, repo, judge_rule):
        judge_rule(RULE)

        assert check(repo, MissingWhyMode.OFF) == RuleTestResult()

    def test_a_gate_needs_no_why(self, repo):
        repo.write(
            ".codeguard/gates/enum-value.yml",
            "id: enum-value\nlanguage: python\nrule:\n  pattern: $X.value\n",
        )

        assert check(repo) == RuleTestResult()
