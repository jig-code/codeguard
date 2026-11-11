from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Self

import pygit2
from pygit2.enums import DeltaStatus, DiffFind, DiffOption

from codeguard.repository.git import Git

_GIT_RENAME_LIMIT = 1000
_WHOLE_FILE_CONTEXT = 2**31 - 1
_TRACKED_DIFF_FLAGS = DiffOption.INDENT_HEURISTIC
_UNTRACKED_DIFF_FLAGS = (
    DiffOption.INCLUDE_UNTRACKED
    | DiffOption.RECURSE_UNTRACKED_DIRS
    | DiffOption.SHOW_UNTRACKED_CONTENT
    | DiffOption.FORCE_TEXT
)


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

    def patches_since(self, merge_base: str) -> list[pygit2.Patch]:
        repository = pygit2.Repository(str(self.root))
        return [
            *self._tracked_patches(repository, merge_base),
            *self._untracked_patches(repository),
        ]

    def tracked_and_untracked_files(self) -> set[str]:
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

    @staticmethod
    def _tracked_patches(repository: pygit2.Repository, merge_base: str) -> list[pygit2.Patch]:
        tree = repository.revparse_single(merge_base).peel(pygit2.Tree)
        diff = tree.diff_to_index(repository.index, _TRACKED_DIFF_FLAGS, _WHOLE_FILE_CONTEXT)
        diff.merge(repository.index.diff_to_workdir(_TRACKED_DIFF_FLAGS, _WHOLE_FILE_CONTEXT))
        diff.find_similar(flags=DiffFind.FIND_RENAMES, rename_limit=_GIT_RENAME_LIMIT)
        return [
            patch
            for patch in diff
            if patch is not None and patch.delta.status != DeltaStatus.DELETED
        ]

    def _untracked_patches(self, repository: pygit2.Repository) -> list[pygit2.Patch]:
        diff = repository.index.diff_to_workdir(_UNTRACKED_DIFF_FLAGS, _WHOLE_FILE_CONTEXT)
        return [
            patch
            for patch in diff
            if patch is not None
            and patch.delta.status == DeltaStatus.UNTRACKED
            and (self.root / patch.delta.new_file.path).is_file()
        ]
