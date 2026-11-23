from dataclasses import dataclass, replace
from functools import cached_property
from importlib.metadata import version
from pathlib import Path
from typing import Self

from packaging.version import Version

from codeguard.ast_grep import AstGrep
from codeguard.config import Config, ConfigError, Ruleset, RulesetLoader
from codeguard.packages import MANIFEST_FILE, GitFetch, Package, Packages
from codeguard.project.cache_directory import cache_directory
from codeguard.project.project import Project

_CODEGUARD_VERSION = Version(version("codeguard"))


@dataclass(frozen=True)
class RulesetResolver:
    root: Path
    config: Config
    ast_grep: AstGrep
    skip_ci_only: bool = False

    @classmethod
    def of(cls, project: Project, skip_ci_only: bool = False) -> Self:
        return cls(project.root, project.config, project.ast_grep, skip_ci_only)

    @cached_property
    def rulesets(self) -> tuple[Ruleset, ...]:
        packages = Packages(
            self.root,
            GitFetch(cache_directory("packages")),
            self.ast_grep.version,
            _CODEGUARD_VERSION,
        )
        rulesets = (RulesetLoader.local(self.root).load(), *packages.rulesets(self.config.packages))
        return tuple(replace(ruleset, skip_ci_only=self.skip_ci_only) for ruleset in rulesets)

    @cached_property
    def own_rulesets(self) -> list[RulesetLoader]:
        package = Package.in_repo(self.root)
        loaders = [RulesetLoader.local(self.root)]
        if package:
            problem = package.version_problem(_CODEGUARD_VERSION, self.ast_grep.version)
            if problem:
                raise ConfigError(f"{self.root / MANIFEST_FILE} is invalid:\n  {problem}")
            loaders.extend(package.ruleset_loader(name) for name in package.manifest.rulesets)
        for loader in loaders:
            loader.check()
        return loaders
