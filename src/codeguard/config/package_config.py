from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from codeguard.config.ruleset_config import RulesetConfig


class GitPackageConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["git"] = "git"
    git: str
    ref: str
    rulesets: dict[str, RulesetConfig] = Field(min_length=1)


class PathPackageConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["path"] = "path"
    # Relative to the repository root.
    path: Path
    rulesets: dict[str, RulesetConfig] = Field(min_length=1)


type PackageConfig = Annotated[GitPackageConfig | PathPackageConfig, Field(discriminator="kind")]
