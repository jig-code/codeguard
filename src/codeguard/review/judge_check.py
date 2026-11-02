from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from codeguard.review.binding import Binding
from codeguard.review.diagnostic import Category, Diagnostic
from codeguard.review.judge import Judge, JudgeError, JudgeRequest
from codeguard.working_tree import AllLines, ChangedLines


@dataclass(frozen=True)
class JudgeCheck:
    root: Path
    binding: Binding
    judge: Judge
    confidence_threshold: float
    scope: ChangedLines | AllLines

    def check(self, files: Sequence[str]) -> list[Diagnostic]:
        matched = self.binding.triggered_files(self.scope, files)
        if not matched:
            return []
        with ThreadPoolExecutor(max_workers=len(matched)) as executor:
            found = executor.map(self._diagnostics, matched)
            return [diagnostic for diagnostics in found for diagnostic in diagnostics]

    def _diagnostics(self, file: str) -> tuple[Diagnostic, ...]:
        try:
            verdict = self.judge.judge(self._request(file)).verdict
        except JudgeError as error:
            return (
                Diagnostic(
                    rule=self.binding.rule,
                    file=file,
                    line=None,
                    message="The judge call failed, so this rule was not checked.",
                    severity=self.binding.severity,
                    note=str(error),
                    category=Category.JUDGE_ERROR,
                    confidence=0.0,
                    error_type=error.error_type,
                ),
            )
        return verdict.diagnostics_for(self.binding, file, self.confidence_threshold)

    def _request(self, file: str) -> JudgeRequest:
        return JudgeRequest.of_change(self.binding, self.root, file, self.scope)
