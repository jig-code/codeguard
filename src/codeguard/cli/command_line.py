from collections.abc import Sequence
from typing import Self, cast

from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import (
    CliApp,
    CliSubCommand,
    SettingsConfigDict,
    SettingsError,
    get_subcommand,
)

from codeguard.cli.config_command import ConfigCommand
from codeguard.cli.eval_command import EvalCommand
from codeguard.cli.review_command import ReviewCommand
from codeguard.cli.rule_tests_command import RuleTestsCommand

type Command = ReviewCommand | RuleTestsCommand | EvalCommand | ConfigCommand


class CommandLineError(Exception):
    @classmethod
    def of(cls, error: ValidationError) -> Self:
        messages = []
        for detail in error.errors():
            fields = detail["loc"][1:]
            text = detail["msg"].removeprefix("Value error, ")
            messages.append(f"--{str(fields[0]).replace('_', '-')}: {text}" if fields else text)
        return cls("; ".join(messages))


class CommandLine(BaseModel):
    model_config = SettingsConfigDict(cli_kebab_case=True, cli_prog_name="codeguard")

    review: CliSubCommand[ReviewCommand] = Field(
        description="Check a project's changed code against the rules it opts into. Runs in the "
        "project: at the agent's Stop and in CI."
    )
    test: CliSubCommand[RuleTestsCommand] = Field(
        description="Test the rules themselves, with no model call: pattern rule and gate tests, "
        "and each judge rule's triggers on its eval cases. For whoever writes rules."
    )
    eval: CliSubCommand[EvalCommand] = Field(
        description="Judge each judge rule's eval cases with its model, to show the rule flags its "
        "invalid cases and passes its valid ones. For whoever writes rules."
    )
    config: CliSubCommand[ConfigCommand] = Field(
        description="Print a setting from .codeguard/config.yaml, or its default."
    )

    @classmethod
    def parse(cls, arguments: Sequence[str]) -> Command:
        try:
            command_line = CliApp.run(cls, cli_args=list(arguments))
        except ValidationError as error:
            raise CommandLineError.of(error) from None
        try:
            command = get_subcommand(command_line, cli_exit_on_error=False)
        except SettingsError as error:
            raise CommandLineError(str(error).removeprefix("Error: ")) from None
        # get_subcommand types its result as any model; CommandLine's fields are the commands.
        return cast(Command, command)
