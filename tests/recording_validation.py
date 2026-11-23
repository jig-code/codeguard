from dataclasses import dataclass, field

from codeguard.rule_validation import ValidationResult


@dataclass
class RecordingValidation:
    result: ValidationResult
    calls: list[str] = field(default_factory=list)

    def run(self) -> ValidationResult:
        self.calls.append("run")
        return self.result


@dataclass
class RecordingSnapshotValidation(RecordingValidation):
    def update_snapshots(self) -> ValidationResult:
        self.calls.append("update_snapshots")
        return self.result
