from recording_judge import RecordingJudge

from codeguard.ast_grep import AstGrep
from codeguard.config import Ruleset
from codeguard.pattern_rules import PatternRuleCheck
from codeguard.repository import AllLines, ChangedLines, LineScopes, WorkingTree
from codeguard.review import CheckStep, JudgeCheck, Review, Reviewer, Verdict
from codeguard.syntax import ChangeClassifier, SyntaxScanner


def review(repo, judge, binding, scope, classification) -> Review:
    local = Ruleset(name=None, root=repo.root / ".codeguard")
    return Reviewer(
        steps=(
            CheckStep(checks=(PatternRuleCheck(repo.root, local),)),
            CheckStep(checks=(JudgeCheck(repo.root, binding, judge, 0.9, scope, classification),)),
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

        result = review(repo, judge, make_binding(), AllLines(("a.py", "b.py")), {})

        assert result == Review(
            diagnostics=(make_diagnostic(), make_diagnostic(judged=True, file="b.py"))
        )
        assert judge.received == [make_judge_request(file="b.py", changes="+     1\tx = 1\n")]

    def test_violations_on_unchanged_lines_are_not_reported(
        self, make_file_classification, repo, make_violation, make_binding
    ):
        repo.write("a.py", "print(1)\nx = 1\ny = 2\n")
        judge = RecordingJudge(
            Verdict(
                reason="The code breaks the convention.",
                violations=(make_violation(lines__start=1, lines__end=2),),
            )
        )

        result = review(
            repo,
            judge,
            make_binding(),
            ChangedLines({"a.py": frozenset({3})}),
            {"a.py": make_file_classification(judged=frozenset({3}))},
        )

        assert result == Review(diagnostics=())

    def test_violation_whose_lines_take_in_a_changed_line_is_reported(
        self, make_file_classification, repo, make_diagnostic, make_violation, make_binding
    ):
        repo.write("a.py", "print(1)\nx = 1\n")
        judge = RecordingJudge(
            Verdict(
                reason="The code breaks the convention.",
                violations=(make_violation(lines__start=1, lines__end=2),),
            )
        )

        result = review(
            repo,
            judge,
            make_binding(),
            ChangedLines({"a.py": frozenset({2})}),
            {"a.py": make_file_classification(judged=frozenset({2}))},
        )

        assert result == Review(
            diagnostics=(make_diagnostic(judged=True, lines__start=1, lines__end=2),)
        )

    def test_unchanged_line_error_does_not_block_the_judge(
        self, repo, make_diagnostic, make_violation, make_judge_request, make_binding
    ):
        repo.write("a.py", "print(1)\n")
        repo.commit("Add a")
        repo.write("a.py", "print(1)\nx = 1\n")
        working_tree = WorkingTree.at(repo.root)
        scope = LineScopes(working_tree).changed_lines("HEAD")
        classification = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree).classify(
            scope
        )
        judge = RecordingJudge(
            Verdict(
                reason="The code breaks the convention.",
                violations=(make_violation(lines__start=2, lines__end=2),),
            )
        )

        result = review(repo, judge, make_binding(), scope, classification)

        assert result == Review(
            diagnostics=(make_diagnostic(judged=True, lines__start=2, lines__end=2),)
        )
        assert judge.received == [make_judge_request(changes="+     2\tx = 1\n")]
