import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from codeguard.ast_grep import AstGrep
from codeguard.config import Ruleset
from codeguard.syntax.parsed_file import ParsedFile
from codeguard.syntax.syntax_scanner import SyntaxScanner
from codeguard.working_tree import ChangedLines, WorkingTree


@dataclass(frozen=True)
class ChangeClassifier:
    scanner: SyntaxScanner
    working_tree: WorkingTree

    @classmethod
    def for_rulesets(
        cls, ast_grep: AstGrep, rulesets: Iterable[Ruleset], working_tree: WorkingTree
    ) -> Self:
        return cls(SyntaxScanner.for_rulesets(ast_grep, rulesets), working_tree)

    def classify(self, scope: ChangedLines) -> ChangedLines:
        head = self.scanner.scan_files(self.working_tree.root, scope.files)
        base = self._base(scope)
        kinds: dict[str, frozenset[str]] = {}
        for file, parsed in head.items():
            added = scope.lines.get(file, frozenset())
            kinds[file] = parsed.touched_kinds(added, base.get(file), scope.removed_lines(file))
        return scope.with_kinds(kinds)

    def _base(self, scope: ChangedLines) -> dict[str, ParsedFile]:
        if scope.base is None:
            return {}
        paths = {file: base_path for file in scope.files if (base_path := scope.base_path(file))}
        contents = self.working_tree.base_contents(scope.base, sorted(set(paths.values())))
        found = [file for file, base_path in paths.items() if base_path in contents]
        with tempfile.TemporaryDirectory() as directory:
            # A renamed file's base is parsed under its new name, to be found by it.
            for file in found:
                path = Path(directory) / file
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(contents[paths[file]])
            return self.scanner.scan_files(Path(directory), found)
