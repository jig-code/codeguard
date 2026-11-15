import subprocess
import tempfile
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from codeguard.repository import ChangedLines, LineScopes, WorkingTree
from codeguard.rule_tests.rule_eval import EditCase
from codeguard.syntax import ChangeClassifier, Classification, SyntaxScanner


@dataclass(frozen=True)
class EditRepo:
    root: Path

    @classmethod
    @contextmanager
    def of(cls, edits: Mapping[str, EditCase]) -> Iterator[Self]:
        with tempfile.TemporaryDirectory() as directory:
            repo = cls(Path(directory))
            repo._git("init")
            repo._write(
                {path: edit.before for path, edit in edits.items() if edit.before is not None}
            )
            repo._git("add", "--all")
            repo._git("commit", "--allow-empty", "--message", "Before")
            repo._write({path: edit.after for path, edit in edits.items()})
            yield repo

    def changed_lines(self) -> ChangedLines:
        return LineScopes.at(WorkingTree.at(self.root)).changed_lines("HEAD")

    def classification(self, scanner: SyntaxScanner, changed: ChangedLines) -> Classification:
        return ChangeClassifier(scanner, WorkingTree.at(self.root)).classify(changed)

    def _write(self, files: Mapping[str, str]) -> None:
        for path, text in files.items():
            file = self.root / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(text)

    def _git(self, *args: str) -> None:
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=codeguard",
                "-c",
                "user.email=codeguard@localhost",
                "-c",
                "commit.gpgsign=false",
                *args,
            ],
            cwd=self.root,
            check=True,
            capture_output=True,
        )
