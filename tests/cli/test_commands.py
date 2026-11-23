import io
import json
from pathlib import Path

import pytest
from recording_validation import RecordingSnapshotValidation

from codeguard.cli.commands import (
    CommandLine,
    CommandLineError,
    ConfigCommand,
    EvalCommand,
    OutputFormat,
    ReviewCommand,
    RuleTestsCommand,
)
from codeguard.config import JudgeChoice, JudgeProvider
from codeguard.repository import LineScopes, WorkingTree
from codeguard.review import Review
from codeguard.rule_validation import RuleValidations, ValidationResult, WhyValidationMode


class TestCommandLine:
    @pytest.mark.parametrize(
        ("arguments", "command"),
        [
            (
                [
                    "review",
                    "--base",
                    "main",
                    "--format",
                    "json",
                    "--judge-errors-as-warnings",
                    "--skip-ci-only",
                    "--host",
                    "codex",
                ],
                ReviewCommand(
                    base="main",
                    format=OutputFormat.JSON,
                    judge_errors_as_warnings=True,
                    skip_ci_only=True,
                    host="codex",
                ),
            ),
            (["review", "--all", "--dry-run"], ReviewCommand(all=True, dry_run=True)),
            (
                ["test", "rules", "-U", "--missing-why", "fail"],
                RuleTestsCommand(
                    package=Path("rules"), update_all=True, missing_why=WhyValidationMode.FAIL
                ),
            ),
            (
                [
                    "eval",
                    "rules",
                    "--repeat",
                    "3",
                    "--rule",
                    "naming",
                    "--rule",
                    "placement",
                    "--case",
                    "invoice",
                    "--provider",
                    "claude-cli",
                    "--model",
                    "claude-haiku-5-5",
                ],
                EvalCommand(
                    package=Path("rules"),
                    repeat=3,
                    rule=["naming", "placement"],
                    case=["invoice"],
                    provider=JudgeProvider.CLAUDE_CLI,
                    model="claude-haiku-5-5",
                ),
            ),
            (
                ["config", "review_time_limit_minutes"],
                ConfigCommand(setting="review_time_limit_minutes"),
            ),
        ],
        ids=["review", "review-all", "test", "eval", "config"],
    )
    def test_each_command_reads_its_flags(self, arguments, command):
        assert CommandLine.parse(arguments) == command

    @pytest.mark.parametrize(
        ("arguments", "message"),
        [
            (["review", "--all", "--base", "main"], "--all is not allowed with --base"),
            (["review", "--dry-run", "--format", "json"], "--format is not allowed with --dry-run"),
            (["eval", "--model", "claude-haiku-5-5"], "--model needs --provider"),
            (["eval", "--repeat", "0"], "--repeat: Input should be greater than or equal to 1"),
            ([], "CLI subcommand is required {review, test, eval, config}"),
        ],
        ids=["all-and-base", "dry-run-and-format", "model-without-provider", "repeat-0", "none"],
    )
    def test_invalid_command_line_is_an_error(self, arguments, message):
        with pytest.raises(CommandLineError) as error:
            CommandLine.parse(arguments)

        assert str(error.value) == message


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


class TestRuleTestsCommand:
    def test_runs_the_validations(self):
        validation = RecordingSnapshotValidation(ValidationResult(warnings=("broad",)))

        result = RuleTestsCommand().results(RuleValidations([validation], []))

        assert result == ValidationResult(warnings=("broad",))
        assert validation.calls == ["run"]

    def test_update_all_updates_the_snapshots(self):
        validation = RecordingSnapshotValidation(ValidationResult())

        RuleTestsCommand(update_all=True).results(RuleValidations([validation], []))

        assert validation.calls == ["update_snapshots"]

    def test_package_is_the_working_tree(self, tmp_path):
        command = RuleTestsCommand(package=tmp_path / "rules")

        assert command.working_tree(Path("/")) == WorkingTree.at(tmp_path / "rules")


class TestEvalCommand:
    @pytest.mark.parametrize(
        ("command", "override"),
        [
            (EvalCommand(), JudgeChoice()),
            (
                EvalCommand(provider=JudgeProvider.CLAUDE_CLI),
                JudgeChoice(provider=JudgeProvider.CLAUDE_CLI),
            ),
            (
                EvalCommand(provider=JudgeProvider.GEMINI),
                JudgeChoice(
                    provider=JudgeProvider.GEMINI, model=JudgeProvider.GEMINI.default_model
                ),
            ),
            (
                EvalCommand(provider=JudgeProvider.CLAUDE_CLI, model="claude-haiku-5-5"),
                JudgeChoice(provider=JudgeProvider.CLAUDE_CLI, model="claude-haiku-5-5"),
            ),
        ],
        ids=["none", "claude-cli-default", "gemini-default", "given-model"],
    )
    def test_judge_override_takes_the_provider_s_default_model(self, command, override):
        assert command.judge_override == override

    def test_package_is_the_working_tree(self, tmp_path):
        command = EvalCommand(package=tmp_path / "rules")

        assert command.working_tree(Path("/")) == WorkingTree.at(tmp_path / "rules")
