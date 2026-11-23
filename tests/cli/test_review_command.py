import io
import json

from codeguard.cli.review_command import OutputFormat, ReviewCommand
from codeguard.repository import LineScopes, WorkingTree
from codeguard.review import Review


class TestReviewCommand:
    def test_scope_is_the_changes_since_the_base(self, git_repo):
        git_repo.git("switch", "--create", "feature")
        git_repo.write("a.py", "x = 1\n")
        git_repo.commit("Add a")
        scopes = LineScopes.at(WorkingTree.at(git_repo.root))

        assert ReviewCommand(base="main").scope(scopes).files == ("a.py",)
        assert ReviewCommand().scope(scopes).files == ()

    def test_scope_with_all_is_every_file(self, git_repo):
        git_repo.write("a.py", "x = 1\n")
        git_repo.commit("Add a")

        scope = ReviewCommand(all=True).scope(LineScopes.at(WorkingTree.at(git_repo.root)))

        assert scope.files == ("a.py",)

    def test_judge_errors_are_reported_as_warnings_only_with_the_flag(self, make_diagnostic):
        review = Review(diagnostics=(make_diagnostic(judge_error=True),))

        assert ReviewCommand().reported(review) == review
        assert ReviewCommand(judge_errors_as_warnings=True).reported(review) == (
            review.with_judge_errors_as_warnings()
        )

    def test_writes_text_lines_by_default(self, make_diagnostic):
        diagnostic = make_diagnostic()
        out = io.StringIO()

        ReviewCommand().write(Review(diagnostics=(diagnostic,)), out)

        assert out.getvalue() == f"{diagnostic}\n"

    def test_writes_one_json_object_with_the_json_format(self, make_diagnostic):
        diagnostic = make_diagnostic()
        out = io.StringIO()

        ReviewCommand(format=OutputFormat.JSON).write(Review(diagnostics=(diagnostic,)), out)

        assert json.loads(out.getvalue()) == {"diagnostics": [diagnostic.as_json()]}
