import yaml

from codeguard.pattern_rules import Layout, PatternRuleTestRunner
from codeguard.rule_tests import RuleTestResult

NO_PRINT_TEST = ".codeguard/rule-tests/no-print-test.yml"
NO_PRINT_SNAPSHOT = ".codeguard/rule-tests/__snapshots__/no-print-snapshot.yml"
LEGACY_NO_PRINT_TEST = ".codeguard/rule-tests/pattern/no-print-test.yml"
STALE_NO_PRINT_SNAPSHOT = (
    ".codeguard/rule-tests/__snapshots__/no-print-snapshot.yml: stale snapshot "
    "entries for no-print. Run codeguard test --update-all."
)


class TestPatternRuleTestRunner:
    def test_run_without_rules_passes(self, tmp_path):
        result = PatternRuleTestRunner(Layout(tmp_path, tmp_path / ".codeguard")).run()

        assert result == RuleTestResult(failed=False)

    def test_run_with_passing_cases_passes(self, repo):
        repo.write(NO_PRINT_TEST, "id: no-print\nvalid:\n  - logging.info(1)\n")

        result = PatternRuleTestRunner(Layout(repo.root, repo.root / ".codeguard")).run()

        assert result == RuleTestResult(failed=False)

    def test_run_with_failing_case_fails(self, repo):
        repo.write(NO_PRINT_TEST, "id: no-print\nvalid:\n  - print(1)\n")

        result = PatternRuleTestRunner(Layout(repo.root, repo.root / ".codeguard")).run()

        assert result == RuleTestResult(failed=True)

    def test_run_with_failing_case_in_the_pattern_directory_fails(self, repo):
        repo.write(LEGACY_NO_PRINT_TEST, "id: no-print\nvalid:\n  - print(1)\n")

        result = PatternRuleTestRunner(Layout(repo.root, repo.root / ".codeguard")).run()

        assert result == RuleTestResult(failed=True)

    def test_update_snapshots_writes_each_directory_its_own_snapshots(self, repo):
        repo.write(NO_PRINT_TEST, "id: no-print\ninvalid:\n  - print(1)\n")
        repo.write(
            ".codeguard/rule-tests/pattern/no-breakpoint-test.yml",
            "id: no-breakpoint\ninvalid:\n  - breakpoint()\n",
        )
        runner = PatternRuleTestRunner(Layout(repo.root, repo.root / ".codeguard"))

        result = runner.update_snapshots()

        assert result == RuleTestResult(failed=False)
        assert (repo.root / NO_PRINT_SNAPSHOT).is_file()
        assert (
            repo.root / ".codeguard/rule-tests/pattern/__snapshots__/no-breakpoint-snapshot.yml"
        ).is_file()
        assert runner.run() == RuleTestResult(failed=False)

    def test_run_reports_snapshot_entry_for_removed_case(self, repo):
        repo.write(NO_PRINT_TEST, "id: no-print\ninvalid:\n  - print(1)\n  - print(2)\n")
        runner = PatternRuleTestRunner(Layout(repo.root, repo.root / ".codeguard"))
        runner.update_snapshots()
        repo.write(NO_PRINT_TEST, "id: no-print\ninvalid:\n  - print(2)\n")

        result = runner.run()

        assert result == RuleTestResult(failed=False, problems=(STALE_NO_PRINT_SNAPSHOT,))

    def test_run_reports_snapshot_of_removed_test(self, repo):
        repo.write(NO_PRINT_TEST, "id: no-print\ninvalid:\n  - print(1)\n")
        runner = PatternRuleTestRunner(Layout(repo.root, repo.root / ".codeguard"))
        runner.update_snapshots()
        (repo.root / NO_PRINT_TEST).unlink()

        result = runner.run()

        assert result == RuleTestResult(failed=False, problems=(STALE_NO_PRINT_SNAPSHOT,))

    def test_update_snapshots_removes_entries_for_removed_cases(self, repo):
        repo.write(NO_PRINT_TEST, "id: no-print\ninvalid:\n  - print(1)\n  - print(2)\n")
        runner = PatternRuleTestRunner(Layout(repo.root, repo.root / ".codeguard"))
        runner.update_snapshots()
        repo.write(NO_PRINT_TEST, "id: no-print\ninvalid:\n  - print(2)\n")

        result = runner.update_snapshots()

        snapshot = yaml.safe_load((repo.root / NO_PRINT_SNAPSHOT).read_text())
        assert result == RuleTestResult(failed=False)
        assert list(snapshot["snapshots"]) == ["print(2)"]

    def test_update_snapshots_removes_snapshot_of_removed_test(self, repo):
        repo.write(NO_PRINT_TEST, "id: no-print\ninvalid:\n  - print(1)\n")
        runner = PatternRuleTestRunner(Layout(repo.root, repo.root / ".codeguard"))
        runner.update_snapshots()
        (repo.root / NO_PRINT_TEST).unlink()

        result = runner.update_snapshots()

        assert result == RuleTestResult(failed=False)
        assert not (repo.root / NO_PRINT_SNAPSHOT).exists()
