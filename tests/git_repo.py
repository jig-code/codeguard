import subprocess
from pathlib import Path
from typing import Self


class Directory:
    def __init__(self, root: Path) -> None:
        self.root = root

    def write(self, path: str, text: str) -> None:
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text)


class GitRepo(Directory):
    @classmethod
    def init(cls, root: Path) -> Self:
        repo = cls(root)
        repo.git("init", "--initial-branch=main")
        repo.git("commit", "--allow-empty", "--message", "Initial commit")
        return repo

    @property
    def file_url(self) -> str:
        return f"file://{self.root}"

    def head(self) -> str:
        return self.git("rev-parse", "HEAD").strip()

    def git(self, *args: str) -> str:
        return subprocess.run(
            [
                "git",
                "-c",
                "user.name=codeguard",
                "-c",
                "user.email=codeguard@example.com",
                "-c",
                "commit.gpgsign=false",
                *args,
            ],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    def commit(self, message: str) -> None:
        self.git("add", "--all")
        self.git("commit", "--message", message)
