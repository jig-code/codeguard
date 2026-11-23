from pathlib import Path
from typing import ClassVar

from pydantic import AliasChoices, BaseModel, Field
from pydantic_settings import CliPositionalArg, CliToggleFlag

from codeguard.repository import WorkingTree
from codeguard.rule_validation import RuleValidations, ValidationResult, WhyValidationMode


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
        return WorkingTree.at_or_containing(self.package, cwd)

    def results(self, validations: RuleValidations) -> ValidationResult:
        return validations.update_snapshots() if self.update_all else validations.run()
