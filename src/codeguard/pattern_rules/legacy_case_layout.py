from dataclasses import dataclass
from pathlib import Path

from codeguard.config import LEGACY_PATTERN_TEST_DIR, LEGACY_RULE_TEST_DIR, PATTERN_CASE_DIR

_OLD_FILES = "*-test.y*ml"


@dataclass(frozen=True)
class LegacyCaseLayout:
    """The layout of pattern rule cases before `pattern-cases/` and `<id>-cases.yml`.

    codeguard reads it for one more release and warns, so a package has time to move.
    """

    root: Path
    ruleset: Path

    def warnings(self) -> tuple[str, ...]:
        target = self.ruleset / PATTERN_CASE_DIR
        legacy = [directory for directory in self._legacy_directories() if _has_cases(directory)]
        return (
            *(self._moved(directory, target, alone=len(legacy) == 1) for directory in legacy),
            *self._renamed(target),
        )

    def _legacy_directories(self) -> list[Path]:
        return [
            directory
            for directory in (
                self.ruleset / LEGACY_RULE_TEST_DIR,
                self.ruleset / LEGACY_PATTERN_TEST_DIR,
            )
            if directory.is_dir()
        ]

    def _moved(self, directory: Path, target: Path, alone: bool) -> str:
        old, new = self._shown(directory), self._shown(target)
        message = (
            f"{old}: pattern rule cases moved to {PATTERN_CASE_DIR}/, and their files from "
            "<id>-test.yml to <id>-cases.yml. codeguard reads the old names for one more release."
        )
        if target.exists() or not alone:
            return f"{message} Move its files into {new}."
        command = f"git mv {old} {new}"
        if _old_files(directory):
            command += f" && {_rename_command(new)}"
        return f"{message} From the repository root, run: {command}"

    def _renamed(self, target: Path) -> tuple[str, ...]:
        if not _old_files(target):
            return ()
        new = self._shown(target)
        return (
            f"{new}: case files moved from <id>-test.yml to <id>-cases.yml. "
            f"From the repository root, run: {_rename_command(new)}",
        )

    def _shown(self, path: Path) -> str:
        return str(path.relative_to(self.root))


def _has_cases(directory: Path) -> bool:
    return any(entry.is_file() or entry.name == "__snapshots__" for entry in directory.iterdir())


def _old_files(directory: Path) -> list[Path]:
    return sorted(directory.glob(_OLD_FILES)) if directory.is_dir() else []


def _rename_command(directory: str) -> str:
    return (
        f'for file in {directory}/{_OLD_FILES}; do git mv "$file" '
        '"${file%-test.*}-cases.${file##*.}"; done'
    )
