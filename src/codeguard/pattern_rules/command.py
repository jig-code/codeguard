import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from codeguard.pattern_rules.layout import Layout

_EXIT_NO_ERRORS = 0
_EXIT_ERRORS_FOUND = 1


@dataclass(frozen=True)
class AstGrepCommand:
    layout: Layout

    def scan(self, files: Sequence[str], options: Sequence[str] = ()) -> str:
        with self.layout.scan_config() as config:
            command = self._command(config, "scan", "--json=stream", *options, *files)
            result = subprocess.run(command, cwd=self.layout.root, capture_output=True, text=True)
        if result.returncode not in (_EXIT_NO_ERRORS, _EXIT_ERRORS_FOUND):
            raise subprocess.CalledProcessError(
                result.returncode, result.args, result.stdout, result.stderr
            )
        return result.stdout

    def test(self) -> bool:
        return self._test()

    def update_snapshots(self) -> bool:
        return self._test("--update-all")

    def _test(self, *options: str) -> bool:
        with self.layout.test_config() as config:
            command = self._command(config, "test", *options)
            return subprocess.run(command, cwd=self.layout.root).returncode == 0

    def _command(self, config: Path, subcommand: str, *args: str) -> list[str | Path]:
        return [*self.layout.ast_grep.executable, subcommand, "--config", config, *args]
