from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from codeguard.config.ruleset_config import RulesetConfig


def _named(rulesets: object) -> object:
    """A list of ruleset names opts into each with every rule, as `{name: {}}` would."""
    if not isinstance(rulesets, list):
        return rulesets
    names = [str(name) for name in rulesets]
    repeated = sorted({name for name in names if names.count(name) > 1})
    if repeated:
        raise ValueError(f"rulesets listed more than once: {', '.join(repeated)}")
    return {name: RulesetConfig() for name in names}


# The rulesets a project opts into: a list of names, or a mapping that sets each one's rules.
type RulesetSelections = Annotated[
    dict[str, RulesetConfig], BeforeValidator(_named), Field(min_length=1)
]


type RepositoryRelativePath = Path


class GitPackageConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["git"] = "git"
    git: str
    ref: str
    rulesets: RulesetSelections


class PathPackageConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["path"] = "path"
    path: RepositoryRelativePath
    rulesets: RulesetSelections


type PackageConfig = Annotated[GitPackageConfig | PathPackageConfig, Field(discriminator="kind")]
