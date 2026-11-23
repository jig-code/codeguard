from pathlib import Path
from typing import ClassVar, Self

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import CliPositionalArg

from codeguard.config import JudgeChoice, JudgeProvider
from codeguard.repository import WorkingTree

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


class EvalCommand(BaseModel):
    name: ClassVar[str] = "eval"

    package: CliPositionalArg[Path | None] = Field(
        default=None,
        description="Evaluate the rule package in this directory instead of the current "
        "repository.",
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
        return JudgeChoice.of_provider(self.provider, self.model)

    def working_tree(self, cwd: Path) -> WorkingTree:
        return WorkingTree.at_or_containing(self.package, cwd)
