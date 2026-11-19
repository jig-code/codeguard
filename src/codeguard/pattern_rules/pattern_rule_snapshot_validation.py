from dataclasses import dataclass

from codeguard.pattern_rules.command import AstGrepCommand
from codeguard.pattern_rules.layout import Layout
from codeguard.pattern_rules.snapshots import SnapshotFile, Snapshots
from codeguard.rule_tests import RuleTestResult

_NO_TESTS = RuleTestResult(failed=False)


@dataclass(frozen=True)
class PatternRuleTestRunner:
    layout: Layout

    def run(self) -> RuleTestResult:
        if not self.layout.has_tests():
            return _NO_TESTS
        stale = self._stale()
        if stale:
            return RuleTestResult(
                failed=False,
                problems=tuple(snapshot.stale_problem(self.layout.root) for snapshot in stale),
            )
        return RuleTestResult(failed=not self._command.test())

    def update_snapshots(self) -> RuleTestResult:
        if not self.layout.has_tests():
            return _NO_TESTS
        for snapshot in self._stale():
            snapshot.path.unlink()
        return RuleTestResult(failed=not self._command.update_snapshots())

    def _stale(self) -> list[SnapshotFile]:
        return [
            snapshot
            for test_dir in self.layout.test_dirs
            for snapshot in Snapshots.load(test_dir).stale()
        ]

    @property
    def _command(self) -> AstGrepCommand:
        return AstGrepCommand(self.layout)
