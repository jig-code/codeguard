from enum import StrEnum
from typing import ClassVar, Self, TextIO

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import CliToggleFlag

from codeguard.repository import LineScope, LineScopes
from codeguard.review import Review


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
