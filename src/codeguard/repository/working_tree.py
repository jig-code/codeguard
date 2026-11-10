from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from codeguard.repository.git import Git


@dataclass(frozen=True)
class WorkingTree:
    git: Git

    @classmethod
    def at(cls, root: Path) -> Self:
        return cls(Git(root))

    @classmethod
    def containing(cls, path: Path) -> Self:
        return cls.at(Path(Git(path).text("rev-parse", "--show-toplevel").strip()))

    @property
    def root(self) -> Path:
        return self.git.root

    def merge_base(self, base: str) -> str:
        return self.git.text("merge-base", base, "HEAD").strip()

    def untracked_files(self) -> set[str]:
        return {
            file
            for file in self.git.paths("ls-files", "--others", "--exclude-standard")
            if (self.root / file).is_file()
        }

    def files(self) -> set[str]:
        """The tracked and untracked files, without the ones the working tree deleted."""
        return {
            file
            for file in self.git.paths("ls-files", "--cached", "--others", "--exclude-standard")
            if (self.root / file).is_file()
        }

    def base_contents(self, base: str, files: Sequence[str]) -> dict[str, bytes]:
        if not files:
            return {}
        in_base = self.git.paths("ls-tree", "-r", "--name-only", base, "--", *files)
        return {file: self.git.bytes("show", f"{base}:{file}") for file in files if file in in_base}

    def git_path(self, name: str) -> Path:
        return self.root / self.git.text("rev-parse", "--git-path", name).strip()
