import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Git:
    root: Path

    def bytes(self, *args: str) -> bytes:
        return subprocess.run(
            ["git", *args], cwd=self.root, stdout=subprocess.PIPE, check=True
        ).stdout

    def text(self, *args: str) -> str:
        return self.bytes(*args).decode(errors="surrogateescape")

    def paths(self, command: str, *args: str) -> set[str]:
        return set(self.text(command, "-z", *args).split("\0")) - {""}
