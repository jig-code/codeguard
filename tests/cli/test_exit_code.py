from codeguard.cli.exit_code import ExitCode


class TestExitCode:
    def test_passed_run_exits_0(self):
        assert ExitCode.of(passed=True) == 0

    def test_failed_run_exits_1(self):
        assert ExitCode.of(passed=False) == 1
