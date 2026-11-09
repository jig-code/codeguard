from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from packaging.version import Version

from codeguard.config import (
    CONFIG_DIR,
    ConfigError,
    GitPackageConfig,
    PackageConfig,
    Ruleset,
    RulesetLoader,
)
from codeguard.packages.git_fetch import GitFetch
from codeguard.packages.manifest import Manifest
from codeguard.packages.selection_check import SelectionCheck


@dataclass(frozen=True)
class Packages:
    working_tree: Path
    fetch: GitFetch
    ast_grep: Version
    codeguard: Version

    def rulesets(self, packages: Sequence[PackageConfig]) -> tuple[Ruleset, ...]:
        return tuple(
            ruleset
            for index, package in enumerate(packages)
            for ruleset in self._rulesets(f"packages.{index}", package)
        )

    def _rulesets(self, location: str, package: PackageConfig) -> Iterator[Ruleset]:
        root = self._root(package)
        manifest = Manifest.load(root)
        codeguard_problem = manifest.codeguard_problem(self.codeguard)
        if codeguard_problem:
            self._fail(f"{location}: {codeguard_problem}")
        ast_grep_problem = manifest.ast_grep_problem(self.ast_grep)
        if ast_grep_problem:
            self._fail(f"{location}: {ast_grep_problem}")
        for name, selection in package.rulesets.items():
            if name not in manifest.rulesets:
                self._fail(f"{location}.rulesets: {manifest.name} has no ruleset {name}")
            ruleset = RulesetLoader(
                repo=root,
                root=root / name,
                name=f"{manifest.name}/{name}",
                selection=selection,
                package_judge=manifest.judge,
            ).load()
            problems = SelectionCheck(ruleset).problems()
            if problems:
                self._fail(*(f"{location}.rulesets.{name}: {problem}" for problem in problems))
            yield ruleset

    def _root(self, package: PackageConfig) -> Path:
        if isinstance(package, GitPackageConfig):
            return self.fetch.fetch(package.git, package.ref)
        return (self.working_tree / package.path).resolve()

    def _fail(self, *problems: str) -> None:
        listed = "".join(f"\n  {problem}" for problem in problems)
        raise ConfigError(f"{self.working_tree / CONFIG_DIR} is invalid:{listed}")
