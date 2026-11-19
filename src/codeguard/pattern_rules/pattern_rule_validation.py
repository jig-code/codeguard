from dataclasses import dataclass

from codeguard.pattern_rules.command import AstGrepCommand
from codeguard.pattern_rules.layout import Layout
from codeguard.pattern_rules.legacy_case_layout import LegacyCaseLayout
from codeguard.pattern_rules.snapshots import SnapshotFile, Snapshots
from codeguard.rule_validation import ValidationResult

_NO_CASES = ValidationResult(failed=False)


@dataclass(frozen=True)
class PatternRuleValidation:
    layout: Layout

    def run(self) -> ValidationResult:
        return ValidationResult.merge([self._legacy_layout_warnings(), self._run()])

    def update_snapshots(self) -> ValidationResult:
        return ValidationResult.merge([self._legacy_layout_warnings(), self._update_snapshots()])

    def _run(self) -> ValidationResult:
        if not self.layout.has_cases():
            return _NO_CASES
        stale = self._stale()
        if stale:
            return ValidationResult(
                failed=False,
                problems=tuple(snapshot.stale_problem(self.layout.root) for snapshot in stale),
            )
        return ValidationResult(failed=not self._command.validate())

    def _update_snapshots(self) -> ValidationResult:
        if not self.layout.has_cases():
            return _NO_CASES
        for snapshot in self._stale():
            snapshot.path.unlink()
        return ValidationResult(failed=not self._command.update_snapshots())

    def _legacy_layout_warnings(self) -> ValidationResult:
        legacy = LegacyCaseLayout(self.layout.root, self.layout.ruleset)
        return ValidationResult(warnings=legacy.warnings())

    def _stale(self) -> list[SnapshotFile]:
        return [
            snapshot
            for case_dir in self.layout.case_dirs
            for snapshot in Snapshots.load(case_dir).stale()
        ]

    @property
    def _command(self) -> AstGrepCommand:
        return AstGrepCommand(self.layout)
