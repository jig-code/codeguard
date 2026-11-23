from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path
from typing import ClassVar, Literal, Self, TextIO

from pydantic import AliasChoices, BaseModel, Field, ValidationError, model_validator
from pydantic_core import ErrorDetails
from pydantic_settings import (
    CliApp,
    CliPositionalArg,
    CliSubCommand,
    CliToggleFlag,
    SettingsConfigDict,
    SettingsError,
    get_subcommand,
)

from codeguard.config import JudgeChoice, JudgeProvider
from codeguard.repository import LineScope, LineScopes, WorkingTree
from codeguard.review import Review
from codeguard.rule_validation import RuleValidations, ValidationResult, WhyValidationMode

_MODEL_HELP = (
    "The model --provider judges with. Default: none for claude-cli, so the claude CLI runs its "
    "own default; "
    + ", ".join(
        f"{provider.default_model} for {provider}"
        for provider in JudgeProvider
        if provider.default_model is not None
    )
    + "."
)


class CommandLineError(Exception):
    pass


class OutputFormat(StrEnum):
    TEXT = "text"
    JSON = "json"


class ReviewCommand(BaseModel):
    name: ClassVar[str] = "review"

    base: str | None = Field(
        default=None,
        description="Include changes since the merge base with this ref, instead of the "
        "uncommitted changes.",
    )
    all: CliToggleFlag[bool] = Field(
        default=False, description="Check every tracked and untracked file."
    )
    dry_run: CliToggleFlag[bool] = Field(
        default=False,
        description="Run the pattern rules and list the judge calls the review would make, "
        "without calling the judge.",
    )
    format: OutputFormat = Field(
        default=OutputFormat.TEXT,
        description="Print diagnostics as text lines or as one JSON object.",
    )
    judge_errors_as_warnings: CliToggleFlag[bool] = Field(
        default=False,
        description="Report each judge call that couldn't complete as a warning, so it doesn't "
        "fail the review.",
    )
    skip_ci_only: CliToggleFlag[bool] = Field(
        default=False,
        description="Skip the rules .codeguard/config.yaml marks ci_only. The agent's Stop hook "
        "passes it; CI and a review run by hand don't.",
    )
    host: str | None = Field(
        default=None,
        description="Name the caller (such as claude-code or codex) in telemetry. Changes "
        "nothing else.",
    )

    @model_validator(mode="after")
    def _one_scope_and_one_output(self) -> Self:
        if self.all and self.base is not None:
            raise ValueError("--all is not allowed with --base")
        if self.dry_run and self.format is not OutputFormat.TEXT:
            raise ValueError("--format is not allowed with --dry-run")
        return self

    def scope(self, scopes: LineScopes) -> LineScope:
        return scopes.all_lines() if self.all else scopes.changed_lines(self.base or "HEAD")

    def reported(self, review: Review) -> Review:
        return review.with_judge_errors_as_warnings() if self.judge_errors_as_warnings else review

    def write(self, review: Review, out: TextIO) -> None:
        if self.format is OutputFormat.JSON:
            review.write_json(out)
        else:
            review.write(out)


class RuleTestsCommand(BaseModel):
    name: ClassVar[str] = "test"

    package: CliPositionalArg[Path | None] = Field(
        default=None,
        description="Test the rule package in this directory instead of the current repository.",
    )
    update_all: CliToggleFlag[bool] = Field(
        default=False,
        validation_alias=AliasChoices("update_all", "U"),
        description="Regenerate snapshots and remove entries for cases that no longer exist.",
    )
    missing_why: WhyValidationMode = Field(
        default=WhyValidationMode.WARN,
        description="Report each rule that doesn't say why it exists as a warning, as a "
        "failure, or not at all.",
    )

    def working_tree(self, cwd: Path) -> WorkingTree:
        return _working_tree(self.package, cwd)

    def results(self, validations: RuleValidations) -> ValidationResult:
        return validations.update_snapshots() if self.update_all else validations.run()


class EvalCommand(BaseModel):
    name: ClassVar[str] = "eval"

    package: CliPositionalArg[Path | None] = Field(
        default=None,
        description="Evaluate the rule package in this directory. Default: the current repository.",
    )
    repeat: int = Field(default=1, ge=1, description="Judge each case this many times.")
    rule: list[str] = Field(
        default_factory=list,
        description="Evaluate only this judge rule. Repeat it for more rules.",
    )
    case: list[str] = Field(
        default_factory=list,
        description="Judge only the cases whose name contains this text. Repeat it to judge the "
        "cases matching any of them.",
    )
    provider: JudgeProvider | None = Field(
        default=None,
        description="Judge every selected rule with this provider instead of its binding's.",
    )
    model: str | None = Field(default=None, description=_MODEL_HELP)

    @model_validator(mode="after")
    def _model_needs_a_provider(self) -> Self:
        if self.model is not None and self.provider is None:
            raise ValueError("--model needs --provider")
        return self

    @property
    def judge_override(self) -> JudgeChoice:
        if self.provider is None:
            return JudgeChoice()
        return JudgeChoice(provider=self.provider, model=self.model or self.provider.default_model)

    def working_tree(self, cwd: Path) -> WorkingTree:
        return _working_tree(self.package, cwd)


class ConfigCommand(BaseModel):
    name: ClassVar[str] = "config"

    setting: CliPositionalArg[Literal["review_time_limit_minutes"]]


type Command = ReviewCommand | RuleTestsCommand | EvalCommand | ConfigCommand


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
            raise CommandLineError(
                "; ".join(_message(detail) for detail in error.errors())
            ) from None
        try:
            get_subcommand(command_line, cli_exit_on_error=False)
        except SettingsError as error:
            raise CommandLineError(str(error).removeprefix("Error: ")) from None
        return next(
            command
            for command in (
                command_line.review,
                command_line.test,
                command_line.eval,
                command_line.config,
            )
            if command is not None
        )


def _message(detail: ErrorDetails) -> str:
    fields = detail["loc"][1:]
    text = detail["msg"].removeprefix("Value error, ")
    return f"--{str(fields[0]).replace('_', '-')}: {text}" if fields else text


def _working_tree(package: Path | None, cwd: Path) -> WorkingTree:
    return WorkingTree.at(package.resolve()) if package else WorkingTree.containing(cwd)
