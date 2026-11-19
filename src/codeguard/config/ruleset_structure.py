from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path, PurePath

from codeguard.config.ruleset import (
    BINDINGS_DIR,
    GATE_DIR,
    JUDGE_EVAL_DIR,
    JUDGE_RULE_DIR,
    LEGACY_PATTERN_TEST_DIR,
    PATTERN_RULE_DIR,
    RULE_TEST_DIR,
    SKILLS_DIR,
    SNAPSHOT_DIR,
)

_DIRECTORIES = frozenset(
    {
        PATTERN_RULE_DIR,
        GATE_DIR,
        SNAPSHOT_DIR,
        LEGACY_PATTERN_TEST_DIR,
        JUDGE_EVAL_DIR,
        JUDGE_RULE_DIR,
        BINDINGS_DIR,
        SKILLS_DIR,
    }
)
_PARENTS = frozenset(str(PurePath(directory).parent) for directory in _DIRECTORIES) - {"."}


@dataclass(frozen=True)
class RulesetStructure:
    root: Path
    files: frozenset[str] = frozenset()

    def problems(self) -> list[str]:
        if not self.root.is_dir():
            return []
        return [f"unexpected {path}" for path in self._unexpected(self.root)]

    def _unexpected(self, directory: Path) -> Iterator[str]:
        for entry in _visible(directory):
            path = str(entry.relative_to(self.root))
            if entry.is_dir() and path in _PARENTS:
                yield from self._unexpected(entry)
            elif not (path in _DIRECTORIES if entry.is_dir() else self._allowed_file(path)):
                yield path

    def _allowed_file(self, path: str) -> bool:
        return path in self.files or str(PurePath(path).parent) == RULE_TEST_DIR


def _visible(directory: Path) -> list[Path]:
    return [entry for entry in sorted(directory.iterdir()) if not entry.name.startswith(".")]
