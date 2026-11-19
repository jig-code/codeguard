from dataclasses import dataclass
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel

_SNAPSHOT_DIR = "__snapshots__"


class _RuleTestFile(BaseModel):
    id: str
    invalid: tuple[str, ...] = ()


class _SnapshotFileContent(BaseModel):
    id: str
    snapshots: dict[str, object]


@dataclass(frozen=True)
class SnapshotFile:
    rule: str
    path: Path
    cases: frozenset[str]

    @classmethod
    def load(cls, path: Path) -> Self:
        content = _SnapshotFileContent.model_validate(yaml.safe_load(path.read_text()))
        return cls(rule=content.id, path=path, cases=frozenset(content.snapshots))

    def stale_problem(self, root: Path) -> str:
        return (
            f"{self.path.relative_to(root)}: stale snapshot entries for {self.rule}. "
            "Run codeguard test --update-all."
        )


@dataclass(frozen=True)
class Snapshots:
    invalid_cases: dict[str, frozenset[str]]
    snapshots: tuple[SnapshotFile, ...]

    @classmethod
    def load(cls, test_dir: Path) -> Self:
        snapshot_paths = sorted((test_dir / _SNAPSHOT_DIR).glob("*.y*ml"))
        test_paths = sorted(test_dir.glob("*.y*ml"))
        tests = [
            _RuleTestFile.model_validate(yaml.safe_load(path.read_text())) for path in test_paths
        ]
        return cls(
            invalid_cases={test.id: frozenset(test.invalid) for test in tests},
            snapshots=tuple(SnapshotFile.load(path) for path in snapshot_paths),
        )

    def stale(self) -> list[SnapshotFile]:
        return [
            snapshot
            for snapshot in self.snapshots
            if not snapshot.cases <= self.invalid_cases.get(snapshot.rule, frozenset())
        ]
