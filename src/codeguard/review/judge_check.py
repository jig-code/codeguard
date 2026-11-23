from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from codeguard.repository import LineScope, WorkingTree
from codeguard.review.binding import Binding
from codeguard.review.diagnostic import Category, Diagnostic
from codeguard.review.judge import Judge, JudgeError, JudgeRequest
from codeguard.review.judge_plan import PlannedCall
from codeguard.syntax import Classification


@dataclass(frozen=True)
class JudgeCheck:
    working_tree: WorkingTree
    binding: Binding
    judge: Judge
    scope: LineScope
    classification: Classification

    def check(self, files: Sequence[str]) -> list[Diagnostic]:
        matched = [file for file in self.binding.files(files) if self._triggered(file)]
        if not matched:
            return []
        with ThreadPoolExecutor(max_workers=len(matched)) as executor:
            found = executor.map(self._diagnostics, matched)
            return [diagnostic for diagnostics in found for diagnostic in diagnostics]

    def plan(
        self, files: Sequence[str], cached: Callable[[JudgeRequest], bool]
    ) -> tuple[PlannedCall, ...]:
        return tuple(
            PlannedCall(
                rule=self.binding.rule,
                file=file,
                cached=cached(self._request(file)),
                triggered=self._triggered(file),
            )
            for file in self.binding.files(files)
        )

    def _triggered(self, file: str) -> bool:
        return self.classification.is_triggered(file, self.binding.triggers)

    def _diagnostics(self, file: str) -> tuple[Diagnostic, ...]:
        try:
            verdict = self.judge.judge(self._request(file)).verdict
        except JudgeError as error:
            return (
                Diagnostic(
                    rule=self.binding.rule,
                    file=file,
                    lines=None,
                    message="The judge call failed, so this rule was not checked.",
                    severity=self.binding.severity,
                    note=str(error),
                    category=Category.JUDGE_ERROR,
                    error_type=error.error_type,
                ),
            )
        return verdict.diagnostics_for(self.binding, file)

    def _request(self, file: str) -> JudgeRequest:
        return JudgeRequest.of_change(
            self.binding, self.working_tree, file, self.scope, self.classification
        )
