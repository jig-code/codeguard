from dataclasses import dataclass
from threading import Barrier

import pytest
from recording_judge import RecordingJudge

from codeguard.config import ChangeKind
from codeguard.repository import AllLines
from codeguard.review import (
    ErrorType,
    JudgeCheck,
    Judgement,
    JudgeNoVerdict,
    JudgeProcessError,
    JudgeTimeout,
    Severity,
    Verdict,
)
from codeguard.syntax import Classification

THRESHOLD = 0.9


@pytest.fixture(autouse=True)
def reviewed_file(tmp_path) -> None:
    (tmp_path / "a.py").write_text("print(1)\n")


@dataclass(frozen=True)
class WaitingJudge:
    barrier: Barrier
    identity: str = "waiting"

    def judge(self, request):
        self.barrier.wait()
        return Judgement(Verdict(reason="The code keeps the convention.", violations=()))


@dataclass(frozen=True)
class FailingJudge:
    error: Exception = JudgeProcessError("claude exited with 1.")
    identity: str = "failing"

    def judge(self, request):
        raise self.error


class TestJudgeCheck:
    def test_failed_judge_call_is_a_judge_error_on_the_file(
        self, tmp_path, make_binding, make_diagnostic
    ):
        check = JudgeCheck(
            tmp_path, make_binding(), FailingJudge(), THRESHOLD, AllLines(()), Classification()
        )

        assert check.check(["a.py"]) == [make_diagnostic(judge_error=True)]

    def test_failed_judge_call_has_the_binding_severity(
        self, tmp_path, make_binding, make_diagnostic
    ):
        check = JudgeCheck(
            tmp_path,
            make_binding(severity=Severity.WARNING),
            FailingJudge(),
            THRESHOLD,
            AllLines(()),
            Classification(),
        )

        assert check.check(["a.py"]) == [
            make_diagnostic(judge_error=True, severity=Severity.WARNING)
        ]

    def test_judge_call_past_the_time_limit_is_a_timeout(self, tmp_path, make_binding):
        error = JudgeTimeout("The review reached its 5-minute time limit.")
        check = JudgeCheck(
            tmp_path, make_binding(), FailingJudge(error), THRESHOLD, AllLines(()), Classification()
        )

        [diagnostic] = check.check(["a.py"])

        assert diagnostic.error_type is ErrorType.TIMEOUT

    def test_judge_call_without_a_verdict_is_no_verdict(self, tmp_path, make_binding):
        error = JudgeNoVerdict("claude returned no verdict.")
        check = JudgeCheck(
            tmp_path, make_binding(), FailingJudge(error), THRESHOLD, AllLines(()), Classification()
        )

        [diagnostic] = check.check(["a.py"])

        assert diagnostic.error_type is ErrorType.NO_VERDICT

    def test_every_file_is_judged_at_the_same_time(self, tmp_path, make_binding):
        files = [f"{index}.py" for index in range(40)]
        for file in files:
            (tmp_path / file).write_text("print(1)\n")
        barrier = Barrier(len(files), timeout=5)

        JudgeCheck(
            tmp_path,
            make_binding(),
            WaitingJudge(barrier),
            THRESHOLD,
            AllLines(()),
            Classification(),
        ).check(files)

        assert not barrier.broken

    def test_no_matching_files_is_no_diagnostics(self, tmp_path, make_binding):
        check = JudgeCheck(
            tmp_path,
            make_binding(paths=("app/**",)),
            RecordingJudge(),
            THRESHOLD,
            AllLines(()),
            Classification(),
        )

        assert check.check(["a.py"]) == []

    def test_each_file_is_its_own_request(self, tmp_path, make_binding, make_judge_request):
        (tmp_path / "b.py").write_text("x = 1\n")
        judge = RecordingJudge()

        JudgeCheck(
            tmp_path, make_binding(), judge, THRESHOLD, AllLines(()), Classification()
        ).check(["a.py", "b.py"])

        assert set(judge.received) == {
            make_judge_request(),
            make_judge_request(file="b.py", changes="+     1\tx = 1\n"),
        }

    def test_judge_gets_the_changed_function_of_the_file(
        self,
        make_changed_lines,
        make_file_classification,
        tmp_path,
        make_binding,
        make_judge_request,
    ):
        (tmp_path / "pricing.py").write_text(
            "DISCOUNT = 5\n\n\ndef discounted(total):\n    return total - DISCOUNT\n"
        )
        judge = RecordingJudge()
        scope = make_changed_lines(return_line_added=True)
        classification = Classification(
            {"pricing.py": make_file_classification(context_lines=frozenset({4, 5}))}
        )

        JudgeCheck(tmp_path, make_binding(), judge, THRESHOLD, scope, classification).check(
            ["pricing.py"]
        )

        assert judge.received == [
            make_judge_request(
                file="pricing.py",
                changes="      4\tdef discounted(total):\n+     5\t    return total - DISCOUNT\n",
            )
        ]

    def test_file_outside_the_binding_paths_is_not_judged(self, tmp_path, make_binding):
        judge = RecordingJudge()

        JudgeCheck(
            tmp_path,
            make_binding(paths=("app/**",)),
            judge,
            THRESHOLD,
            AllLines(()),
            Classification(),
        ).check(["a.py"])

        assert judge.received == []

    def test_file_whose_changes_miss_the_triggers_is_not_judged(
        self, make_new_file_changed_lines, make_file_classification, tmp_path, make_binding
    ):
        judge = RecordingJudge()
        scope = make_new_file_changed_lines()
        classification = Classification(
            {
                "a.py": make_file_classification(
                    touched_kinds=frozenset({ChangeKind.COMMENT, ChangeKind.ANY})
                )
            }
        )
        binding = make_binding(triggers=frozenset({ChangeKind.CLASS_HEADER}))

        JudgeCheck(tmp_path, binding, judge, THRESHOLD, scope, classification).check(["a.py"])

        assert judge.received == []

    def test_file_whose_changes_touch_a_trigger_is_judged(
        self,
        make_new_file_changed_lines,
        make_file_classification,
        tmp_path,
        make_binding,
        make_judge_request,
    ):
        judge = RecordingJudge()
        scope = make_new_file_changed_lines()
        classification = Classification(
            {
                "a.py": make_file_classification(
                    touched_kinds=frozenset({ChangeKind.COMMENT, ChangeKind.ANY})
                )
            }
        )
        binding = make_binding(triggers=frozenset({ChangeKind.COMMENT, ChangeKind.CLASS_HEADER}))

        JudgeCheck(tmp_path, binding, judge, THRESHOLD, scope, classification).check(["a.py"])

        assert judge.received == [make_judge_request()]

    def test_file_without_change_kinds_is_judged(
        self, make_new_file_changed_lines, tmp_path, make_binding, make_judge_request
    ):
        (tmp_path / "a.md").write_text("# A\n")
        judge = RecordingJudge()
        binding = make_binding(triggers=frozenset({ChangeKind.CLASS_HEADER}))
        scope = make_new_file_changed_lines(file="a.md", content=b"# A\n")

        JudgeCheck(tmp_path, binding, judge, THRESHOLD, scope, Classification()).check(["a.md"])

        assert judge.received == [make_judge_request(file="a.md", changes="+     1\t# A\n")]

    def test_binding_without_triggers_judges_every_changed_file(
        self,
        make_new_file_changed_lines,
        make_file_classification,
        tmp_path,
        make_binding,
        make_judge_request,
    ):
        judge = RecordingJudge()
        scope = make_new_file_changed_lines()
        classification = Classification(
            {
                "a.py": make_file_classification(
                    touched_kinds=frozenset({ChangeKind.COMMENT, ChangeKind.ANY})
                )
            }
        )

        JudgeCheck(tmp_path, make_binding(), judge, THRESHOLD, scope, classification).check(
            ["a.py"]
        )

        assert judge.received == [make_judge_request()]

    def test_diagnostics_have_the_binding_severity(
        self, tmp_path, make_binding, make_violation, make_diagnostic
    ):
        judge = RecordingJudge(
            Verdict(reason="The code breaks the convention.", violations=(make_violation(),))
        )
        check = JudgeCheck(
            tmp_path,
            make_binding(severity=Severity.WARNING),
            judge,
            THRESHOLD,
            AllLines(()),
            Classification(),
        )

        assert check.check(["a.py"]) == [make_diagnostic(judged=True, severity=Severity.WARNING)]

    def test_error_below_the_threshold_is_a_warning(
        self, tmp_path, make_binding, make_violation, make_diagnostic
    ):
        judge = RecordingJudge(
            Verdict(
                reason="The code breaks the convention.",
                violations=(make_violation(confidence=0.5),),
            )
        )
        check = JudgeCheck(
            tmp_path, make_binding(), judge, THRESHOLD, AllLines(()), Classification()
        )

        assert check.check(["a.py"]) == [
            make_diagnostic(judged=True, severity=Severity.WARNING, confidence=0.5)
        ]
