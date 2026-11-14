import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from codeguard.ast_grep import AstGrep
from codeguard.config import Ruleset
from codeguard.repository import ChangedLines, WorkingTree
from codeguard.syntax.classification import Classification, FileClassification
from codeguard.syntax.parsed_file import ParsedFile
from codeguard.syntax.syntax_scanner import SyntaxScanner


@dataclass(frozen=True)
class ChangeClassifier:
    scanner: SyntaxScanner
    working_tree: WorkingTree

    @classmethod
    def for_rulesets(
        cls, ast_grep: AstGrep, rulesets: Iterable[Ruleset], working_tree: WorkingTree
    ) -> Self:
        return cls(SyntaxScanner.for_rulesets(ast_grep, rulesets), working_tree)

    def classify(self, scope: ChangedLines) -> Classification:
        head = self.scanner.scan_files(self.working_tree.root, scope.files)
        base = self._base(scope)
        return Classification(
            {
                file: FileClassification.of_change(diff, head.get(file), base.get(file))
                for file, diff in scope.diffs.items()
            }
        )

    def _base(self, scope: ChangedLines) -> dict[str, ParsedFile]:
        if scope.base is None:
            return {}
        base_paths = {file: diff.base_path for file, diff in scope.diffs.items() if diff.base_path}
        contents = self.working_tree.base_contents(scope.base, sorted(set(base_paths.values())))
        found = [file for file, base_path in base_paths.items() if base_path in contents]
        with tempfile.TemporaryDirectory() as directory:
            for file in found:
                head_path = Path(directory) / file
                head_path.parent.mkdir(parents=True, exist_ok=True)
                head_path.write_bytes(contents[base_paths[file]])
            return self.scanner.scan_files(Path(directory), found)
