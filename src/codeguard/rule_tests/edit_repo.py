import subprocess
import tempfile
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from codeguard.line_scope import ChangedLines, LineScopes
from codeguard.rule_tests.rule_eval import EditCase
from codeguard.syntax import ChangeClassifier, SyntaxScanner
from codeguard.working_tree import WorkingTree


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

    def classified(self, scanner: SyntaxScanner) -> ChangedLines:
        working_tree = WorkingTree.at(self.root)
        return ChangeClassifier(scanner, working_tree).classify(
            LineScopes(working_tree).changed_lines("HEAD")
        )

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
