from dataclasses import dataclass

from codeguard.repository.git import Git
from codeguard.repository.unified_diff import Hunk, parse

_PINNED_CONFIG = (
    "core.quotePath=false",
    "diff.renames=true",
    "diff.renameLimit=1000",
    "diff.interHunkContext=0",
)
_PINNED_OPTIONS = (
    "--no-color",
    "--no-ext-diff",
    "--no-textconv",
    "--diff-algorithm=myers",
    "--indent-heuristic",
    "--submodule=short",
    "--ignore-submodules=untracked",
)
_CHANGED_ROWS_ONLY = ("-U0", "--no-prefix", "--diff-filter=d")


@dataclass(frozen=True)
class PinnedDiff:
    """git's diff of the working tree, the same whatever the user's git config sets."""

    git: Git

    def hunks(self, base: str) -> tuple[Hunk, ...]:
        """The hunks the working tree changes since `base`, without context rows and
        without the files it deletes."""
        return parse(self._run(*_CHANGED_ROWS_ONLY, base))

    def _run(self, *args: str) -> str:
        config = [option for setting in _PINNED_CONFIG for option in ("-c", setting)]
        return self.git.text(*config, "diff", *_PINNED_OPTIONS, *args)
