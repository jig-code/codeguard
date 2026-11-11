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
                file: _classify_file(scope, file, head[file], base.get(file))
                if file in head
                else FileClassification(touched_kinds=None, context_lines=scope.points(file))
                for file in scope.files
            }
        )

    def _base(self, scope: ChangedLines) -> dict[str, ParsedFile]:
        if scope.base is None:
            return {}
        base_paths = {
            file: base_path for file in scope.files if (base_path := scope.base_path(file))
        }
        contents = self.working_tree.base_contents(scope.base, sorted(set(base_paths.values())))
        found = [file for file, base_path in base_paths.items() if base_path in contents]
        with tempfile.TemporaryDirectory() as directory:
            for file in found:
                head_path = Path(directory) / file
                head_path.parent.mkdir(parents=True, exist_ok=True)
                head_path.write_bytes(contents[base_paths[file]])
            return self.scanner.scan_files(Path(directory), found)


def _classify_file(
    scope: ChangedLines, file: str, parsed: ParsedFile, before: ParsedFile | None
) -> FileClassification:
    added = scope.lines.get(file, frozenset())
    removed_code = scope.removed_code_lines(file)
    context_lines = parsed.judged_lines(added)
    kind_lines = parsed.kind_lines(added)
    if before is not None:
        replaced_rows = scope.replaced_base_rows(file)
        context_lines |= scope.head_lines(
            file, before.judged_lines(removed_code, replaced=replaced_rows)
        )
        for kind, lines in before.kind_lines(removed_code, replaced=replaced_rows).items():
            kind_lines[kind] = kind_lines.get(kind, frozenset()) | scope.head_lines(file, lines)
    return FileClassification(
        parsed.touched_kinds(added, before, removed_code), context_lines, kind_lines
    )
