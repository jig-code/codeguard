from collections.abc import Sequence
from dataclasses import dataclass

from codeguard.rule_tests.rule_test_result import RuleTestResult
from codeguard.rule_tests.test_runner import SnapshotTestRunner, TestRunner


@dataclass(frozen=True)
class RuleTests:
    snapshot_runners: Sequence[SnapshotTestRunner]
    runners: Sequence[TestRunner]

    def run(self) -> RuleTestResult:
        return RuleTestResult.merge(
            runner.run() for runner in (*self.snapshot_runners, *self.runners)
        )

    def update_snapshots(self) -> RuleTestResult:
        return RuleTestResult.merge(
            (
                *(runner.update_snapshots() for runner in self.snapshot_runners),
                *(runner.run() for runner in self.runners),
            )
        )
