from typing import Protocol

from codeguard.rule_validation.validation_result import ValidationResult


class Validation(Protocol):
    def run(self) -> ValidationResult: ...


class SnapshotValidation(Validation, Protocol):
    def update_snapshots(self) -> ValidationResult: ...
