import os
from pathlib import Path
from unittest import mock

import pytest

from codeguard.cli.command_line import CommandLine, CommandLineError
from codeguard.cli.config_command import ConfigCommand
from codeguard.cli.eval_command import EvalCommand
from codeguard.cli.review_command import OutputFormat, ReviewCommand
from codeguard.cli.rule_tests_command import RuleTestsCommand
from codeguard.config import JudgeProvider
from codeguard.rule_validation import WhyValidationMode


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

    @pytest.mark.parametrize(
        ("command", "entry"),
        [
            (
                "review",
                "  --format {text,json}  Print diagnostics as text lines or as one JSON object.\n"
                "                        (default: text)\n",
            ),
            (
                "test",
                "  --missing-why {warn,fail,off}\n"
                "                        Report each rule that doesn't say why it exists as a\n"
                "                        warning, as a failure, or not at all. (default: warn)\n",
            ),
            (
                "eval",
                "  --provider {claude-cli,gemini,bedrock,codex-cli}\n"
                "                        Judge every selected rule with this provider instead\n"
                "                        of its binding's. (default: None)\n",
            ),
        ],
        ids=["format", "missing-why", "provider"],
    )
    @mock.patch.dict(os.environ, {"COLUMNS": "80"})
    def test_help_gives_an_enum_flag_s_choices_and_default_by_value(self, command, entry, capsys):
        with pytest.raises(SystemExit) as exit_:
            CommandLine.parse([command, "--help"])

        assert exit_.value.code == 0
        assert entry in capsys.readouterr().out
