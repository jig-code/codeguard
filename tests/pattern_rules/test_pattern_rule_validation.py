import yaml

from codeguard.pattern_rules import Layout, PatternRuleValidation
from codeguard.rule_validation import ValidationResult

NO_PRINT_TEST = ".codeguard/pattern-cases/no-print-cases.yml"
NO_PRINT_SNAPSHOT = ".codeguard/pattern-cases/__snapshots__/no-print-snapshot.yml"
LEGACY_NO_PRINT_TEST = ".codeguard/rule-tests/pattern/no-print-test.yml"
RENAME_LEGACY_FILES = (
    "for file in .codeguard/pattern-cases/*-test.y*ml; "
    'do git mv "$file" "${file%-test.*}-cases.${file##*.}"; done'
)
MOVED = (
    "pattern rule cases moved to pattern-cases/, and their files from <id>-test.yml to "
    "<id>-cases.yml. codeguard reads the old names for one more release."
)
MERGE_LEGACY_PATTERN_DIR = (
    f".codeguard/rule-tests/pattern: {MOVED} Move its files into .codeguard/pattern-cases."
)
STALE_NO_PRINT_SNAPSHOT = (
    ".codeguard/pattern-cases/__snapshots__/no-print-snapshot.yml: stale snapshot "
    "entries for no-print. Run codeguard validate --update-all."
)


class TestPatternRuleValidation:
    def test_run_without_rules_passes(self, tmp_path):
        result = PatternRuleValidation(Layout(tmp_path, tmp_path / ".codeguard")).run()

        assert result == ValidationResult(failed=False)

    def test_run_with_passing_cases_passes(self, repo):
        repo.write(NO_PRINT_TEST, "id: no-print\nvalid:\n  - logging.info(1)\n")

        result = PatternRuleValidation(Layout(repo.root, repo.root / ".codeguard")).run()

        assert result == ValidationResult(failed=False)

    def test_run_with_failing_case_fails(self, repo):
        repo.write(NO_PRINT_TEST, "id: no-print\nvalid:\n  - print(1)\n")

        result = PatternRuleValidation(Layout(repo.root, repo.root / ".codeguard")).run()

        assert result == ValidationResult(failed=True)

    def test_run_reads_cases_in_the_legacy_pattern_directory_and_warns(self, repo):
        repo.write(LEGACY_NO_PRINT_TEST, "id: no-print\nvalid:\n  - print(1)\n")

        result = PatternRuleValidation(Layout(repo.root, repo.root / ".codeguard")).run()

        assert result == ValidationResult(
            failed=True,
            warnings=(
                f".codeguard/rule-tests/pattern: {MOVED} From the repository root, run: "
                f"git mv .codeguard/rule-tests/pattern .codeguard/pattern-cases && "
                f"{RENAME_LEGACY_FILES}",
            ),
        )

    def test_run_reads_cases_in_the_legacy_directory_and_warns(self, repo):
        repo.write(
            ".codeguard/rule-tests/no-print-test.yml", "id: no-print\nvalid:\n  - print(1)\n"
        )

        result = PatternRuleValidation(Layout(repo.root, repo.root / ".codeguard")).run()

        assert result == ValidationResult(
            failed=True,
            warnings=(
                f".codeguard/rule-tests: {MOVED} From the repository root, run: "
                f"git mv .codeguard/rule-tests .codeguard/pattern-cases && {RENAME_LEGACY_FILES}",
            ),
        )

    def test_run_warns_to_move_a_legacy_directory_with_new_file_names(self, repo):
        repo.write(
            ".codeguard/rule-tests/no-print-cases.yml",
            "id: no-print\nvalid:\n  - logging.info(1)\n",
        )

        result = PatternRuleValidation(Layout(repo.root, repo.root / ".codeguard")).run()

        assert result == ValidationResult(
            failed=False,
            warnings=(
                f".codeguard/rule-tests: {MOVED} From the repository root, run: "
                "git mv .codeguard/rule-tests .codeguard/pattern-cases",
            ),
        )

    def test_run_warns_to_merge_a_legacy_directory_into_an_existing_new_one(self, repo):
        repo.write(NO_PRINT_TEST, "id: no-print\nvalid:\n  - logging.info(1)\n")
        repo.write(
            ".codeguard/rule-tests/no-breakpoint-cases.yml",
            "id: no-breakpoint\nvalid:\n  - logging.info(1)\n",
        )

        result = PatternRuleValidation(Layout(repo.root, repo.root / ".codeguard")).run()

        assert result == ValidationResult(
            failed=False,
            warnings=(
                f".codeguard/rule-tests: {MOVED} Move its files into .codeguard/pattern-cases.",
            ),
        )

    def test_run_warns_of_old_file_names_in_the_new_directory(self, repo):
        repo.write(
            ".codeguard/pattern-cases/no-print-test.yml",
            "id: no-print\nvalid:\n  - logging.info(1)\n",
        )

        result = PatternRuleValidation(Layout(repo.root, repo.root / ".codeguard")).run()

        assert result == ValidationResult(
            failed=False,
            warnings=(
                ".codeguard/pattern-cases: case files moved from <id>-test.yml to "
                f"<id>-cases.yml. From the repository root, run: {RENAME_LEGACY_FILES}",
            ),
        )

    def test_update_snapshots_writes_each_directory_its_own_snapshots(self, repo):
        repo.write(NO_PRINT_TEST, "id: no-print\ninvalid:\n  - print(1)\n")
        repo.write(
            ".codeguard/rule-tests/pattern/no-breakpoint-test.yml",
            "id: no-breakpoint\ninvalid:\n  - breakpoint()\n",
        )
        validation = PatternRuleValidation(Layout(repo.root, repo.root / ".codeguard"))

        result = validation.update_snapshots()

        assert result == ValidationResult(failed=False, warnings=(MERGE_LEGACY_PATTERN_DIR,))
        assert (repo.root / NO_PRINT_SNAPSHOT).is_file()
        assert (
            repo.root / ".codeguard/rule-tests/pattern/__snapshots__/no-breakpoint-snapshot.yml"
        ).is_file()
        assert validation.run() == ValidationResult(
            failed=False, warnings=(MERGE_LEGACY_PATTERN_DIR,)
        )

    def test_run_reports_snapshot_entry_for_removed_case(self, repo):
        repo.write(NO_PRINT_TEST, "id: no-print\ninvalid:\n  - print(1)\n  - print(2)\n")
        validation = PatternRuleValidation(Layout(repo.root, repo.root / ".codeguard"))
        validation.update_snapshots()
        repo.write(NO_PRINT_TEST, "id: no-print\ninvalid:\n  - print(2)\n")

        result = validation.run()

        assert result == ValidationResult(failed=False, problems=(STALE_NO_PRINT_SNAPSHOT,))

    def test_run_reports_snapshot_of_removed_test(self, repo):
        repo.write(NO_PRINT_TEST, "id: no-print\ninvalid:\n  - print(1)\n")
        validation = PatternRuleValidation(Layout(repo.root, repo.root / ".codeguard"))
        validation.update_snapshots()
        (repo.root / NO_PRINT_TEST).unlink()

        result = validation.run()

        assert result == ValidationResult(failed=False, problems=(STALE_NO_PRINT_SNAPSHOT,))

    def test_update_snapshots_removes_entries_for_removed_cases(self, repo):
        repo.write(NO_PRINT_TEST, "id: no-print\ninvalid:\n  - print(1)\n  - print(2)\n")
        validation = PatternRuleValidation(Layout(repo.root, repo.root / ".codeguard"))
        validation.update_snapshots()
        repo.write(NO_PRINT_TEST, "id: no-print\ninvalid:\n  - print(2)\n")

        result = validation.update_snapshots()

        snapshot = yaml.safe_load((repo.root / NO_PRINT_SNAPSHOT).read_text())
        assert result == ValidationResult(failed=False)
        assert list(snapshot["snapshots"]) == ["print(2)"]

    def test_update_snapshots_removes_snapshot_of_removed_test(self, repo):
        repo.write(NO_PRINT_TEST, "id: no-print\ninvalid:\n  - print(1)\n")
        validation = PatternRuleValidation(Layout(repo.root, repo.root / ".codeguard"))
        validation.update_snapshots()
        (repo.root / NO_PRINT_TEST).unlink()

        result = validation.update_snapshots()

        assert result == ValidationResult(failed=False)
        assert not (repo.root / NO_PRINT_SNAPSHOT).exists()
