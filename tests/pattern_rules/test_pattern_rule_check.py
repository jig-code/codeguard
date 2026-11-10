from dataclasses import replace

import pytest

from codeguard.config import (
    PatternBindingConfig,
    PatternBindingsConfig,
    RuleOverride,
    Ruleset,
    RulesetConfig,
)
from codeguard.pattern_rules import PatternRuleCheck
from codeguard.review import Severity


@pytest.fixture
def tests_excluded() -> PatternBindingsConfig:
    return PatternBindingsConfig(
        {
            "no-print.yaml": PatternBindingConfig(
                rule="no-print", paths=("**/*.py",), exclude_paths=("tests/**",)
            )
        }
    )


def packaged_ruleset(root, selection: RulesetConfig = RulesetConfig()) -> Ruleset:
    return Ruleset(name="example/python", root=root / ".codeguard", selection=selection)


class TestPatternRuleCheck:
    def test_check_reports_violations_for_given_files_only(self, repo, make_diagnostic):
        repo.write("checked.py", "import os\nprint(os.name)\n")
        repo.write("unchecked.py", "print(1)\n")
        ruleset = Ruleset(name=None, root=repo.root / ".codeguard")

        diagnostics = PatternRuleCheck(repo.root, ruleset).check(["checked.py"])

        assert diagnostics == [make_diagnostic(file="checked.py", lines__start=2, lines__end=2)]

    def test_check_with_no_files_reports_nothing(self, repo):
        repo.write("unchecked.py", "print(1)\n")
        ruleset = Ruleset(name=None, root=repo.root / ".codeguard")

        diagnostics = PatternRuleCheck(repo.root, ruleset).check([])

        assert diagnostics == []

    def test_check_without_rules_reports_nothing(self, tmp_path):
        (tmp_path / "module.py").write_text("print(1)\n")
        ruleset = Ruleset(name=None, root=tmp_path / ".codeguard")

        diagnostics = PatternRuleCheck(tmp_path, ruleset).check(["module.py"])

        assert diagnostics == []

    def test_packaged_rule_is_named_by_its_ruleset(self, repo, make_diagnostic):
        repo.write("a.py", "print(1)\n")

        diagnostics = PatternRuleCheck(repo.root, packaged_ruleset(repo.root)).check(["a.py"])

        assert diagnostics == [make_diagnostic(rule="example/python/no-print")]

    def test_excluded_rule_reports_nothing(self, repo):
        repo.write("a.py", "print(1)\n")
        ruleset = packaged_ruleset(repo.root, RulesetConfig(exclude=("no-print",)))

        diagnostics = PatternRuleCheck(repo.root, ruleset).check(["a.py"])

        assert diagnostics == []

    def test_rule_left_out_of_include_reports_nothing(self, repo, make_diagnostic):
        repo.write("a.py", "print(1)\nbreakpoint()\n")
        ruleset = packaged_ruleset(repo.root, RulesetConfig(include=("no-print",)))

        diagnostics = PatternRuleCheck(repo.root, ruleset).check(["a.py"])

        assert diagnostics == [make_diagnostic(rule="example/python/no-print")]

    def test_ci_only_rule_reports_in_ci(self, repo, make_diagnostic):
        repo.write("a.py", "print(1)\n")
        selection = RulesetConfig(rules={"no-print": RuleOverride(ci_only=True)})

        diagnostics = PatternRuleCheck(repo.root, packaged_ruleset(repo.root, selection)).check(
            ["a.py"]
        )

        assert diagnostics == [make_diagnostic(rule="example/python/no-print")]

    def test_skipped_ci_only_rule_reports_nothing(self, repo):
        repo.write("a.py", "print(1)\n")
        selection = RulesetConfig(rules={"no-print": RuleOverride(ci_only=True)})
        ruleset = replace(packaged_ruleset(repo.root, selection), skip_ci_only=True)

        diagnostics = PatternRuleCheck(repo.root, ruleset).check(["a.py"])

        assert diagnostics == []

    def test_overridden_severity_applies(self, repo, make_diagnostic):
        repo.write("a.py", "breakpoint()\n")
        selection = RulesetConfig(rules={"no-breakpoint": RuleOverride(severity=Severity.ERROR)})

        diagnostics = PatternRuleCheck(repo.root, packaged_ruleset(repo.root, selection)).check(
            ["a.py"]
        )

        assert diagnostics == [
            make_diagnostic(
                warning=True, rule="example/python/no-breakpoint", severity=Severity.ERROR
            )
        ]

    def test_ruleset_severity_sets_a_rule_without_an_override(self, repo, make_diagnostic):
        repo.write("a.py", "print(1)\n")
        selection = RulesetConfig(severity=Severity.WARNING)

        diagnostics = PatternRuleCheck(repo.root, packaged_ruleset(repo.root, selection)).check(
            ["a.py"]
        )

        assert diagnostics == [
            make_diagnostic(rule="example/python/no-print", severity=Severity.WARNING)
        ]

    def test_rule_severity_wins_over_the_ruleset_severity(self, repo, make_diagnostic):
        repo.write("a.py", "print(1)\n")
        selection = RulesetConfig(
            severity=Severity.WARNING, rules={"no-print": RuleOverride(severity=Severity.ERROR)}
        )

        diagnostics = PatternRuleCheck(repo.root, packaged_ruleset(repo.root, selection)).check(
            ["a.py"]
        )

        assert diagnostics == [make_diagnostic(rule="example/python/no-print")]

    def test_overridden_paths_limit_the_rule(self, repo, make_diagnostic):
        repo.write("app/a.py", "print(1)\n")
        repo.write("scripts/b.py", "print(1)\n")
        selection = RulesetConfig(rules={"no-print": RuleOverride(paths=("app/**",))})

        diagnostics = PatternRuleCheck(repo.root, packaged_ruleset(repo.root, selection)).check(
            ["app/a.py", "scripts/b.py"]
        )

        assert diagnostics == [make_diagnostic(rule="example/python/no-print", file="app/a.py")]

    def test_binding_excluded_paths_limit_the_rule(self, repo, make_diagnostic, tests_excluded):
        repo.write("app/a.py", "print(1)\n")
        repo.write("tests/test_a.py", "print(1)\n")
        ruleset = Ruleset(name=None, root=repo.root / ".codeguard", pattern_bindings=tests_excluded)

        diagnostics = PatternRuleCheck(repo.root, ruleset).check(["app/a.py", "tests/test_a.py"])

        assert diagnostics == [make_diagnostic(file="app/a.py")]

    def test_overridden_excluded_paths_replace_the_binding(
        self, repo, make_diagnostic, tests_excluded
    ):
        repo.write("tests/test_a.py", "print(1)\n")
        selection = RulesetConfig(rules={"no-print": RuleOverride(exclude_paths=())})
        ruleset = Ruleset(
            name=None,
            root=repo.root / ".codeguard",
            selection=selection,
            pattern_bindings=tests_excluded,
        )

        diagnostics = PatternRuleCheck(repo.root, ruleset).check(["tests/test_a.py"])

        assert diagnostics == [make_diagnostic(file="tests/test_a.py")]
