import pytest
from recording_judge import RecordingJudge, RecordingJudges

from codeguard.ast_grep import AstGrep
from codeguard.config import Config, ConfigError, JudgeProvider
from codeguard.project import Project, ProjectReview, ProviderJudges
from codeguard.repository import AllLines, WorkingTree
from codeguard.review import CachedJudges, JudgePlan, PlannedCall


@pytest.fixture
def project(directory) -> Project:
    return Project(WorkingTree.at(directory.root), Config(), AstGrep())


class TestProjectReview:
    def test_review_needs_the_gemini_sign_in_even_when_no_file_matches_the_gemini_binding(
        self, directory, project, make_judge_rule, make_ruleset, store
    ):
        directory.write("rules/judge/responsibility-placement.md", make_judge_rule().text)
        ruleset = make_ruleset(
            root=project.root,
            binding__provider=JudgeProvider.GEMINI,
            binding__model="gemini-judge-test",
            binding__paths=("**/*.rb",),
        )
        review = ProjectReview(
            project,
            (ruleset,),
            CachedJudges(ProviderJudges(), store),
        )

        with pytest.raises(ConfigError) as error:
            review.review(AllLines(("a.py",)))

        assert str(error.value) == "Gemini needs a project: set CODEGUARD_JUDGE__GEMINI__PROJECT"

    def test_plan_lists_a_gemini_judge_call_without_a_gemini_sign_in(
        self, directory, project, make_judge_rule, make_ruleset, store
    ):
        directory.write("rules/judge/responsibility-placement.md", make_judge_rule().text)
        directory.write("a.py", "x = 1\n")
        ruleset = make_ruleset(
            root=project.root,
            binding__provider=JudgeProvider.GEMINI,
            binding__model="gemini-judge-test",
        )
        review = ProjectReview(
            project,
            (ruleset,),
            CachedJudges(ProviderJudges(), store),
        )

        plan = review.plan(AllLines(("a.py",)))

        assert plan == JudgePlan(
            calls=(
                PlannedCall(
                    rule="responsibility-placement", file="a.py", cached=False, triggered=True
                ),
            )
        )

    def test_second_review_reuses_the_cached_verdict(
        self, directory, project, make_judge_rule, make_ruleset, store
    ):
        directory.write("rules/judge/responsibility-placement.md", make_judge_rule().text)
        directory.write("a.py", "x = 1\n")
        judge = RecordingJudge()
        review = ProjectReview(
            project,
            (make_ruleset(root=project.root),),
            CachedJudges(RecordingJudges(judge), store),
        )
        review.review(AllLines(("a.py",)))

        review.review(AllLines(("a.py",)))

        assert [request.file for request in judge.received] == ["a.py"]
