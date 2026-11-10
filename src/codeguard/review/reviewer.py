from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from codeguard.review.diagnostic import Diagnostic
from codeguard.review.review import Review
from codeguard.working_tree import AllLines, ChangedLines


class Step(Protocol):
    def run(
        self, files: Sequence[str], diagnostics: tuple[Diagnostic, ...]
    ) -> tuple[Diagnostic, ...]: ...


@dataclass(frozen=True)
class Reviewer:
    steps: tuple[Step, ...]

    def run(self, scope: ChangedLines | AllLines) -> Review:
        diagnostics: tuple[Diagnostic, ...] = ()
        for step in self.steps:
            found = step.run(scope.files, diagnostics)
            diagnostics = tuple(
                diagnostic
                for diagnostic in found
                if scope.covers(diagnostic.file, diagnostic.lines)
            )
        return Review(diagnostics=diagnostics)
