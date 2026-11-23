import os
from pathlib import Path


def cache_directory(name: str) -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(base) / "codeguard" / name
