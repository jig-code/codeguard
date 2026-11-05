from recording_judge import RecordingJudge

from codeguard.config import Ruleset
from codeguard.pattern_rules import PatternRuleCheck
from codeguard.review import CheckStep, JudgeCheck, Review, Reviewer, Verdict
from codeguard.working_tree import AllLines, ChangedLines


def review(repo, judge, binding, scope) -> Review:
    local = Ruleset(name=None, root=repo.root / ".codeguard")
    return Reviewer(
        steps=(
            CheckStep(checks=(PatternRuleCheck(repo.root, local),)),
            CheckStep(checks=(JudgeCheck(repo.root, binding, judge, 0.9, scope),)),
        )
    ).run(scope)


class TestReviewer:
    def test_judge_runs_after_checks_on_files_that_passed(
        self, repo, make_diagnostic, make_violation, make_judge_request, make_binding
    ):
        repo.write("a.py", "print(1)\n")
        repo.write("b.py", "x = 1\n")
        judge = RecordingJudge(
            Verdict(
                reason="The code breaks the convention.", violations=(make_violation(file="b.py"),)
            )
        )

        result = review(repo, judge, make_binding(), AllLines(("a.py", "b.py")))

        assert result == Review(
            diagnostics=(make_diagnostic(), make_diagnostic(judged=True, file="b.py"))
        )
        assert judge.received == [make_judge_request(file="b.py", changes="+     1\tx = 1\n")]

    def test_violations_on_unchanged_lines_are_not_reported(
        self, repo, make_violation, make_binding
    ):
        repo.write("a.py", "print(1)\nx = 1\n")
        judge = RecordingJudge(
            Verdict(reason="The code breaks the convention.", violations=(make_violation(line=1),))
        )

        result = review(repo, judge, make_binding(), ChangedLines({"a.py": frozenset({2})}))

        assert result == Review(diagnostics=())

    def test_unchanged_line_error_does_not_block_the_judge(
        self, repo, make_diagnostic, make_violation, make_judge_request, make_binding
    ):
        repo.write("a.py", "print(1)\nx = 1\n")
        judge = RecordingJudge(
            Verdict(reason="The code breaks the convention.", violations=(make_violation(line=2),))
        )

        result = review(repo, judge, make_binding(), ChangedLines({"a.py": frozenset({2})}))

        assert result == Review(diagnostics=(make_diagnostic(judged=True, line=2),))
        assert judge.received == [make_judge_request(changes="+     2\tx = 1\n")]
