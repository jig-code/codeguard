import yaml

from codeguard.pattern_rules import Layout, PatternRuleValidation
from codeguard.rule_validation import ValidationResult

NO_PRINT_TEST = ".codeguard/rule-tests/no-print-test.yml"
NO_PRINT_SNAPSHOT = ".codeguard/rule-tests/__snapshots__/no-print-snapshot.yml"
LEGACY_NO_PRINT_TEST = ".codeguard/rule-tests/pattern/no-print-test.yml"
STALE_NO_PRINT_SNAPSHOT = (
    ".codeguard/rule-tests/__snapshots__/no-print-snapshot.yml: stale snapshot "
    "entries for no-print. Run codeguard test --update-all."
)


class TestPatternRuleValidation:
    def test_run_without_rules_passes(self, tmp_path):
        result = PatternRuleValidation(Layout(tmp_path, tmp_path / ".codeguard")).run()

        assert result == ValidationResult(failed=False)

    def test_run_with_passing_cases_passes(self, repo):
        repo.write(NO_PRINT_TEST, yaml.safe_dump({"id": "no-print", "valid": ["logging.info(1)"]}))

        result = PatternRuleValidation(Layout(repo.root, repo.root / ".codeguard")).run()

        assert result == ValidationResult(failed=False)

    def test_run_with_failing_case_fails(self, repo):
        repo.write(NO_PRINT_TEST, yaml.safe_dump({"id": "no-print", "valid": ["print(1)"]}))

        result = PatternRuleValidation(Layout(repo.root, repo.root / ".codeguard")).run()

        assert result == ValidationResult(failed=True)

    def test_run_with_failing_case_in_the_pattern_directory_fails(self, repo):
        repo.write(LEGACY_NO_PRINT_TEST, yaml.safe_dump({"id": "no-print", "valid": ["print(1)"]}))

        result = PatternRuleValidation(Layout(repo.root, repo.root / ".codeguard")).run()

        assert result == ValidationResult(failed=True)

    def test_update_snapshots_writes_each_directory_its_own_snapshots(self, repo):
        repo.write(NO_PRINT_TEST, yaml.safe_dump({"id": "no-print", "invalid": ["print(1)"]}))
        repo.write(
            ".codeguard/rule-tests/pattern/no-breakpoint-test.yml",
            yaml.safe_dump({"id": "no-breakpoint", "invalid": ["breakpoint()"]}),
        )
        validation = PatternRuleValidation(Layout(repo.root, repo.root / ".codeguard"))

        result = validation.update_snapshots()

        assert result == ValidationResult(failed=False)
        assert (repo.root / NO_PRINT_SNAPSHOT).is_file()
        assert (
            repo.root / ".codeguard/rule-tests/pattern/__snapshots__/no-breakpoint-snapshot.yml"
        ).is_file()
        assert validation.run() == ValidationResult(failed=False)

    def test_update_snapshots_covers_the_gate_tests(self, repo):
        repo.write(
            ".codeguard/gates/enum-value.yml",
            yaml.safe_dump(
                {"id": "enum-value", "language": "python", "rule": {"pattern": "$X.value"}}
            ),
        )
        repo.write(
            ".codeguard/rule-tests/enum-value-test.yml",
            yaml.safe_dump(
                {"id": "enum-value", "valid": ["status.name"], "invalid": ["status.value"]}
            ),
        )
        validation = PatternRuleValidation(Layout(repo.root, repo.root / ".codeguard"))

        result = validation.update_snapshots()

        assert result == ValidationResult(failed=False)
        assert (repo.root / ".codeguard/rule-tests/__snapshots__/enum-value-snapshot.yml").is_file()

    def test_run_reports_snapshot_entry_for_removed_case(self, repo):
        repo.write(
            NO_PRINT_TEST, yaml.safe_dump({"id": "no-print", "invalid": ["print(1)", "print(2)"]})
        )
        validation = PatternRuleValidation(Layout(repo.root, repo.root / ".codeguard"))
        validation.update_snapshots()
        repo.write(NO_PRINT_TEST, yaml.safe_dump({"id": "no-print", "invalid": ["print(2)"]}))

        result = validation.run()

        assert result == ValidationResult(failed=False, problems=(STALE_NO_PRINT_SNAPSHOT,))

    def test_run_reports_snapshot_of_removed_test(self, repo):
        repo.write(NO_PRINT_TEST, yaml.safe_dump({"id": "no-print", "invalid": ["print(1)"]}))
        validation = PatternRuleValidation(Layout(repo.root, repo.root / ".codeguard"))
        validation.update_snapshots()
        (repo.root / NO_PRINT_TEST).unlink()

        result = validation.run()

        assert result == ValidationResult(failed=False, problems=(STALE_NO_PRINT_SNAPSHOT,))

    def test_update_snapshots_removes_entries_for_removed_cases(self, repo):
        repo.write(
            NO_PRINT_TEST, yaml.safe_dump({"id": "no-print", "invalid": ["print(1)", "print(2)"]})
        )
        validation = PatternRuleValidation(Layout(repo.root, repo.root / ".codeguard"))
        validation.update_snapshots()
        repo.write(NO_PRINT_TEST, yaml.safe_dump({"id": "no-print", "invalid": ["print(2)"]}))

        result = validation.update_snapshots()

        snapshot = yaml.safe_load((repo.root / NO_PRINT_SNAPSHOT).read_text())
        assert result == ValidationResult(failed=False)
        assert list(snapshot["snapshots"]) == ["print(2)"]

    def test_update_snapshots_removes_snapshot_of_removed_test(self, repo):
        repo.write(NO_PRINT_TEST, yaml.safe_dump({"id": "no-print", "invalid": ["print(1)"]}))
        validation = PatternRuleValidation(Layout(repo.root, repo.root / ".codeguard"))
        validation.update_snapshots()
        (repo.root / NO_PRINT_TEST).unlink()

        result = validation.update_snapshots()

        assert result == ValidationResult(failed=False)
        assert not (repo.root / NO_PRINT_SNAPSHOT).exists()
