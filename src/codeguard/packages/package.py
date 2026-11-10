from dataclasses import dataclass
from pathlib import Path
from typing import Self

from packaging.version import Version

from codeguard.config import RulesetConfig, RulesetLoader
from codeguard.packages.manifest import MANIFEST_FILE, Manifest


@dataclass(frozen=True)
class Package:
    root: Path
    manifest: Manifest

    @classmethod
    def load(cls, root: Path) -> Self:
        return cls(root, Manifest.load(root))

    @classmethod
    def in_repo(cls, root: Path) -> Self | None:
        return cls.load(root) if (root / MANIFEST_FILE).is_file() else None

    def version_problem(self, codeguard: Version, ast_grep: Version) -> str | None:
        return self.manifest.codeguard_problem(codeguard) or self.manifest.ast_grep_problem(
            ast_grep
        )

    def ruleset_loader(self, name: str, selection: RulesetConfig | None = None) -> RulesetLoader:
        return RulesetLoader(
            repo=self.root,
            root=self.root / name,
            name=f"{self.manifest.name}/{name}",
            selection=selection or RulesetConfig(),
            package_judge=self.manifest.judge,
        )
