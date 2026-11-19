from dataclasses import dataclass, field

from codeguard.rule_tests import RuleTestResult, RuleTests


@dataclass
class RecordingRunner:
    result: RuleTestResult
    calls: list[str] = field(default_factory=list)

    def run(self) -> RuleTestResult:
        self.calls.append("run")
        return self.result


@dataclass
class RecordingSnapshotRunner(RecordingRunner):
    def update_snapshots(self) -> RuleTestResult:
        self.calls.append("update_snapshots")
        return self.result


class TestRuleTests:
    def test_update_snapshots_updates_snapshot_runners_and_runs_the_others(self):
        snapshot_runner = RecordingSnapshotRunner(RuleTestResult(problems=("stale",)))
        runner = RecordingRunner(RuleTestResult(warnings=("broad",)))

        result = RuleTests(snapshot_runners=[snapshot_runner], runners=[runner]).update_snapshots()

        assert snapshot_runner.calls == ["update_snapshots"]
        assert runner.calls == ["run"]
        assert result == RuleTestResult(problems=("stale",), warnings=("broad",))

    def test_run_runs_every_runner(self):
        snapshot_runner = RecordingSnapshotRunner(RuleTestResult(failed=True))
        runner = RecordingRunner(RuleTestResult())

        result = RuleTests(snapshot_runners=[snapshot_runner], runners=[runner]).run()

        assert snapshot_runner.calls == ["run"]
        assert runner.calls == ["run"]
        assert result == RuleTestResult(failed=True)
