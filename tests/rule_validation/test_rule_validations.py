from recording_validation import RecordingSnapshotValidation, RecordingValidation

from codeguard.rule_validation import RuleValidations, ValidationResult


class TestRuleValidations:
    def test_update_snapshots_updates_snapshot_validations_and_runs_the_others(self):
        snapshot_validation = RecordingSnapshotValidation(ValidationResult(problems=("stale",)))
        validation = RecordingValidation(ValidationResult(warnings=("broad",)))

        result = RuleValidations(
            snapshot_validations=[snapshot_validation], validations=[validation]
        ).update_snapshots()

        assert snapshot_validation.calls == ["update_snapshots"]
        assert validation.calls == ["run"]
        assert result == ValidationResult(problems=("stale",), warnings=("broad",))

    def test_run_runs_every_validation(self):
        snapshot_validation = RecordingSnapshotValidation(ValidationResult(failed=True))
        validation = RecordingValidation(ValidationResult())

        result = RuleValidations(
            snapshot_validations=[snapshot_validation], validations=[validation]
        ).run()

        assert snapshot_validation.calls == ["run"]
        assert validation.calls == ["run"]
        assert result == ValidationResult(failed=True)
