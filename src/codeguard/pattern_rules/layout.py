import tempfile
from collections.abc import Iterator, Sequence
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from pathlib import Path

import yaml

from codeguard.ast_grep import AstGrep
from codeguard.config import GATE_DIR, LEGACY_PATTERN_TEST_DIR, PATTERN_RULE_DIR, RULE_TEST_DIR


@dataclass(frozen=True)
class Layout:
    root: Path
    ruleset: Path
    ast_grep: AstGrep = AstGrep()

    @property
    def rule_dir(self) -> Path:
        return self.ruleset / PATTERN_RULE_DIR

    @property
    def test_dirs(self) -> list[Path]:
        candidates = (self.ruleset / RULE_TEST_DIR, self.ruleset / LEGACY_PATTERN_TEST_DIR)
        return [directory for directory in candidates if directory.is_dir()]

    @property
    def tested_rule_dirs(self) -> list[Path]:
        candidates = (self.rule_dir, self.ruleset / GATE_DIR)
        return [directory for directory in candidates if directory.is_dir()]

    def has_rules(self) -> bool:
        return self.rule_dir.is_dir()

    def has_tests(self) -> bool:
        return bool(self.tested_rule_dirs) and bool(self.test_dirs)

    def scan_config(self) -> AbstractContextManager[Path]:
        return self._config([self.rule_dir])

    def test_config(self) -> AbstractContextManager[Path]:
        return self._config(self.tested_rule_dirs)

    @contextmanager
    def _config(self, rule_dirs: Sequence[Path]) -> Iterator[Path]:
        settings = {
            "ruleDirs": [str(directory) for directory in rule_dirs],
            "testConfigs": [{"testDir": str(directory)} for directory in self.test_dirs],
        }
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "sgconfig.yml"
            config.write_text(yaml.safe_dump(settings))
            yield config
