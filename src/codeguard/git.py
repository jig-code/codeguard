import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Git:
    """Runs git in one directory."""

    root: Path

    def bytes(self, *args: str) -> bytes:
        return subprocess.run(
            ["git", *args], cwd=self.root, stdout=subprocess.PIPE, check=True
        ).stdout

    def text(self, *args: str) -> str:
        # Decoded without newline translation, so only "\n" ends a row, as it does for git.
        return self.bytes(*args).decode(errors="surrogateescape")

    def paths(self, command: str, *args: str) -> set[str]:
        return set(self.text(command, "-z", *args).split("\0")) - {""}
