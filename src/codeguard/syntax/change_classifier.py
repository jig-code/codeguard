import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from codeguard.ast_grep import AstGrep
from codeguard.config import Ruleset
from codeguard.repository import ChangedLines, WorkingTree
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

    def classify(self, scope: ChangedLines) -> ChangedLines:
        head = self.scanner.scan_files(self.working_tree.root, scope.files)
        base = self._base(scope)
        kinds: dict[str, frozenset[str]] = {}
        judged: dict[str, frozenset[int]] = {}
        kind_lines: dict[str, dict[str, frozenset[int]]] = {}
        for file, parsed in head.items():
            added = scope.lines.get(file, frozenset())
            removed = frozenset(
                line for removal in scope.removals_in(file) for line in removal.base_lines
            )
            before = base.get(file)
            kinds[file] = parsed.touched_kinds(added, before, removed)
            judged[file] = parsed.judged_lines(added)
            kind_lines[file] = parsed.kind_lines(added)
            if before is None:
                continue
            # A removal shows the code around it that the change kept, not the code beside it.
            gone = scope.removed_base_lines(file)
            judged[file] |= _in_head(scope, file, before.judged_lines(removed, gone))
            for kind, lines in before.kind_lines(removed, gone).items():
                kind_lines[file][kind] = kind_lines[file].get(kind, frozenset()) | _in_head(
                    scope, file, lines
                )
        return scope.with_kinds(kinds).with_judged_lines(judged).with_kind_lines(kind_lines)

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


def _in_head(scope: ChangedLines, file: str, base_lines: Iterable[int]) -> frozenset[int]:
    return frozenset(
        line for base_line in base_lines if (line := scope.head_line(file, base_line)) is not None
    )
