import os
import subprocess
import sys
import traceback
from collections.abc import Sequence
from pathlib import Path

import logfire
import pydantic_ai

from codeguard.cli.command_line import CommandLine, CommandLineError
from codeguard.cli.config_command import ConfigCommand
from codeguard.cli.eval_command import EvalCommand
from codeguard.cli.exit_code import ExitCode
from codeguard.cli.review_command import ReviewCommand
from codeguard.cli.rule_tests_command import RuleTestsCommand
from codeguard.config import ConfigLoader
from codeguard.file_lock import exclusive_lock
from codeguard.project import (
    Project,
    ProjectReview,
    ProjectValidations,
    check_installed_evals,
)
from codeguard.repository import LineScopes, WorkingTree

_REVIEW_LOCK = "codeguard-review.lock"


def main() -> int:
    _configure_telemetry()
    return run(sys.argv[1:])


def run(arguments: Sequence[str]) -> int:
    try:
        command = CommandLine.parse(arguments)
    except CommandLineError as error:
        sys.stderr.write(f"codeguard: error: {error}\n")
        return ExitCode.ERROR
    try:
        if isinstance(command, ConfigCommand):
            return _config(command)
        with logfire.span("codeguard {command}", command=command.name):
            return _dispatch(command)
    except subprocess.CalledProcessError as error:
        if error.stdout:
            sys.stderr.write(error.stdout)
        if error.stderr:
            sys.stderr.write(error.stderr)
        traceback.print_exc()
        return ExitCode.ERROR
    except Exception:
        traceback.print_exc()
        return ExitCode.ERROR


def _configure_telemetry() -> None:
    logfire.configure(
        send_to_logfire="if-token-present",
        service_name="codeguard",
        environment="ci" if os.environ.get("GITHUB_ACTIONS") == "true" else "local",
        console=False,
        inspect_arguments=False,
    )
    logfire.instrument_pydantic_ai()
    # codeguard's output is what the hooks and --format json read, so pydantic-ai prints nothing.
    pydantic_ai.BANNER_ENABLED = False


def _dispatch(command: ReviewCommand | RuleTestsCommand | EvalCommand) -> int:
    match command:
        case ReviewCommand():
            return _review(command)
        case RuleTestsCommand():
            return _test(command)
        case EvalCommand():
            return _eval(command)


def _review(command: ReviewCommand) -> int:
    working_tree = WorkingTree.containing(Path.cwd())
    review = ProjectReview.of(Project.load(working_tree), command.skip_ci_only)
    if command.dry_run:
        scope = command.scope(LineScopes.at(working_tree))
        result = review.check_patterns(scope)
        result.write(sys.stdout)
        review.plan(scope).write(sys.stdout)
        return ExitCode.of(not result.blocks)
    with exclusive_lock(working_tree.git_path(_REVIEW_LOCK)):
        scope = command.scope(LineScopes.at(working_tree))
        with logfire.span(
            "review {repository}",
            repository=working_tree.root.name,
            files=len(scope.files),
            host=command.host,
        ) as span:
            result = command.reported(review.review(scope))
            span.set_attributes(
                {
                    "diagnostics": len(result.diagnostics),
                    "errors": sum(diagnostic.blocks for diagnostic in result.diagnostics),
                }
            )
    command.write(result, sys.stdout)
    return ExitCode.of(not result.blocks)


def _test(command: RuleTestsCommand) -> int:
    validations = ProjectValidations.of(Project.load(command.working_tree(Path.cwd())))
    result = command.results(validations.validations(command.missing_why))
    result.write(sys.stdout)
    return ExitCode.of(result.passed)


def _eval(command: EvalCommand) -> int:
    check_installed_evals()
    # pydantic-evals takes about 0.4s to import, so only codeguard eval loads it.
    from codeguard.judge_evals import EvalSelection  # noqa: PLC0415
    from codeguard.project.rule_evaluation import RuleEvaluation  # noqa: PLC0415

    evaluation = RuleEvaluation.of(Project.load(command.working_tree(Path.cwd())))
    result = evaluation.run(
        command.repeat,
        EvalSelection(frozenset(command.rule), tuple(command.case)),
        command.judge_override,
    )
    result.write(sys.stdout)
    return ExitCode.of(result.passed)


def _config(command: ConfigCommand) -> int:
    config = ConfigLoader(WorkingTree.containing(Path.cwd()).root).load()
    sys.stdout.write(f"{getattr(config, command.setting)}\n")
    return ExitCode.PASSED
