import os
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from codeguard.repository.git import Git

# A commit needs an author, and a temporary repository has no user config to take one from.
_COMMIT_AUTHOR = (
    "-c",
    "user.name=codeguard",
    "-c",
    "user.email=codeguard@localhost",
    "-c",
    "commit.gpgsign=false",
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

    @classmethod
    @contextmanager
    def temporary(cls, before: Mapping[str, str], after: Mapping[str, str]) -> Iterator[Self]:
        """A repository whose HEAD holds `before` and whose working tree holds `after`, so
        the difference between them is an uncommitted change."""
        with tempfile.TemporaryDirectory() as directory:
            tree = cls.at(Path(directory))
            tree.git.run("init")
            tree._write(before)
            tree.git.run("add", "--all")
            tree.git.run(*_COMMIT_AUTHOR, "commit", "--allow-empty", "--message", "Before")
            tree._write(after)
            yield tree

    @property
    def root(self) -> Path:
        return self.git.root

    def merge_base(self, base: str) -> str:
        return self.git.text("merge-base", base, "HEAD").strip()

    def untracked_files(self) -> set[str]:
        return self._files("--others", "--exclude-standard")

    def tracked_and_untracked_files(self) -> set[str]:
        return self._files("--cached", "--others", "--exclude-standard")

    def contents(self, file: str) -> bytes:
        path = self.root / file
        return os.fsencode(os.readlink(path)) if path.is_symlink() else path.read_bytes()

    def base_contents(self, base: str, files: Sequence[str]) -> dict[str, bytes]:
        if not files:
            return {}
        in_base = self.git.paths("ls-tree", "-r", "--name-only", base, "--", *files)
        return {file: self.git.bytes("show", f"{base}:{file}") for file in files if file in in_base}

    def git_path(self, name: str) -> Path:
        return self.root / self.git.text("rev-parse", "--git-path", name).strip()

    def _write(self, files: Mapping[str, str]) -> None:
        for path, text in files.items():
            file = self.root / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(text)

    def _files(self, *ls_files_args: str) -> set[str]:
        return {
            file
            for file in self.git.paths("ls-files", *ls_files_args)
            if (self.root / file).is_file()
        }
