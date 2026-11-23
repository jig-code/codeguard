from pathlib import Path

from recording_validation import RecordingSnapshotValidation

from codeguard.cli.rule_tests_command import RuleTestsCommand
from codeguard.repository import WorkingTree
from codeguard.rule_validation import RuleValidations, ValidationResult


class TestRuleTestsCommand:
    def test_runs_the_validations(self):
        validation = RecordingSnapshotValidation(ValidationResult(warnings=("broad",)))

        result = RuleTestsCommand().results(RuleValidations([validation], []))

        assert result == ValidationResult(warnings=("broad",))
        assert validation.calls == ["run"]

    def test_update_all_updates_the_snapshots(self):
        validation = RecordingSnapshotValidation(ValidationResult())

        RuleTestsCommand(update_all=True).results(RuleValidations([validation], []))

        assert validation.calls == ["update_snapshots"]

    def test_package_is_the_working_tree(self, tmp_path):
        command = RuleTestsCommand(package=tmp_path / "rules")

        assert command.working_tree(Path("/")) == WorkingTree.at(tmp_path / "rules")
