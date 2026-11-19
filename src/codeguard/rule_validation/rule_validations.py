from collections.abc import Sequence
from dataclasses import dataclass

from codeguard.rule_validation.validation import SnapshotValidation, Validation
from codeguard.rule_validation.validation_result import ValidationResult


@dataclass(frozen=True)
class RuleValidations:
    snapshot_validations: Sequence[SnapshotValidation]
    validations: Sequence[Validation]

    def run(self) -> ValidationResult:
        return ValidationResult.merge(
            validation.run() for validation in (*self.snapshot_validations, *self.validations)
        )

    def update_snapshots(self) -> ValidationResult:
        return ValidationResult.merge(
            (
                *(validation.update_snapshots() for validation in self.snapshot_validations),
                *(validation.run() for validation in self.validations),
            )
        )
