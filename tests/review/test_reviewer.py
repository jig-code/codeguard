from recording_judge import RecordingJudge

from codeguard.ast_grep import AstGrep
from codeguard.config import Ruleset
from codeguard.pattern_rules import PatternRuleCheck
from codeguard.repository import AllLines, ChangedLines, FileDiff, LineScopes, WorkingTree
from codeguard.repository.file_diff import AddedRow, KeptRow
from codeguard.review import CheckStep, JudgeCheck, Review, Reviewer, Verdict
from codeguard.syntax import ChangeClassifier, Classification, SyntaxScanner


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

        scope = AllLines(("a.py", "b.py"))
        local = Ruleset(name=None, root=repo.root / ".codeguard")
        reviewer = Reviewer(
            steps=(
                CheckStep(checks=(PatternRuleCheck(repo.root, local),)),
                CheckStep(
                    checks=(
                        JudgeCheck(repo.root, make_binding(), judge, 0.9, scope, Classification()),
                    )
                ),
            )
        )

        result = reviewer.run(scope)

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

        rows = [KeptRow(1, 1), KeptRow(2, 2), AddedRow(3, text=b"y = 2")]
        scope = ChangedLines({"a.py": FileDiff.from_whole_file_rows("a.py", rows)})
        classification = Classification(
            {"a.py": make_file_classification(context_lines=frozenset({3}))}
        )
        local = Ruleset(name=None, root=repo.root / ".codeguard")
        reviewer = Reviewer(
            steps=(
                CheckStep(checks=(PatternRuleCheck(repo.root, local),)),
                CheckStep(
                    checks=(
                        JudgeCheck(repo.root, make_binding(), judge, 0.9, scope, classification),
                    )
                ),
            )
        )

        result = reviewer.run(scope)

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

        rows = [KeptRow(1, 1), AddedRow(2, text=b"x = 1")]
        scope = ChangedLines({"a.py": FileDiff.from_whole_file_rows("a.py", rows)})
        classification = Classification(
            {"a.py": make_file_classification(context_lines=frozenset({2}))}
        )
        local = Ruleset(name=None, root=repo.root / ".codeguard")
        reviewer = Reviewer(
            steps=(
                CheckStep(checks=(PatternRuleCheck(repo.root, local),)),
                CheckStep(
                    checks=(
                        JudgeCheck(repo.root, make_binding(), judge, 0.9, scope, classification),
                    )
                ),
            )
        )

        result = reviewer.run(scope)

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

        local = Ruleset(name=None, root=repo.root / ".codeguard")
        reviewer = Reviewer(
            steps=(
                CheckStep(checks=(PatternRuleCheck(repo.root, local),)),
                CheckStep(
                    checks=(
                        JudgeCheck(repo.root, make_binding(), judge, 0.9, scope, classification),
                    )
                ),
            )
        )

        result = reviewer.run(scope)

        assert result == Review(
            diagnostics=(make_diagnostic(judged=True, lines__start=2, lines__end=2),)
        )
        assert judge.received == [make_judge_request(changes="+     2\tx = 1\n")]
