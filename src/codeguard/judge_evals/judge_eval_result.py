from collections.abc import Iterable
from dataclasses import dataclass
from typing import Self, TextIO

from pydantic_evals.reporting import EvaluationReport
from rich.console import Console

from codeguard.rule_tests import EditCase, EditReview, RuleTestResult

type RuleEvalReport = EvaluationReport[EditCase, EditReview, None]


@dataclass(frozen=True)
class JudgeEvalResult:
    reports: tuple[RuleEvalReport, ...] = ()
    checks: RuleTestResult = RuleTestResult()

    @classmethod
    def merge(cls, results: Iterable[Self]) -> Self:
        collected = list(results)
        return cls(
            reports=tuple(report for result in collected for report in result.reports),
            checks=RuleTestResult.merge(result.checks for result in collected),
        )

    @property
    def passed(self) -> bool:
        return self.checks.passed and all(_passed(report) for report in self.reports)

    @property
    def failures(self) -> tuple[str, ...]:
        return tuple(failure for report in self.reports for failure in _failures(report))

    @property
    def reasons(self) -> tuple[str, ...]:
        """The judge's reason for each case it judged, passing or failing, so whoever reads the
        eval can see on what ground the rule was decided and fix its wording."""
        return tuple(
            f"{report.dataset_name} {case.name}: {case.output.reason}"
            for report in self.reports
            for case in report.cases
            if case.output.reason is not None
        )

    def write(self, out: TextIO) -> None:
        console = Console(file=out)
        for report in self.reports:
            report.print(console=console, include_reasons=True)
        for reason in self.reasons:
            print(reason, file=out)
        for failure in self.failures:
            print(failure, file=out)
        self.checks.write(out)


def _passed(report: RuleEvalReport) -> bool:
    averages = report.averages()
    return (
        not report.failures
        and not any(case.evaluator_failures for case in report.cases)
        and averages is not None
        and averages.assertions == 1.0
    )


def _failures(report: RuleEvalReport) -> list[str]:
    rule = report.dataset_name
    failed = [
        f"{rule} {case.name}: {result.reason}"
        for case in report.cases
        for result in case.assertions.values()
        if not result.value
    ]
    not_evaluated = [
        f"{rule} {case.name}: {failure.name} failed: {failure.error_message}"
        for case in report.cases
        for failure in case.evaluator_failures
    ]
    not_judged = [
        f"{rule} {failure.name}: not judged: {failure.error_message}" for failure in report.failures
    ]
    evaluated = report.averages() is not None or report.failures
    empty = [] if evaluated else [f"{rule}: no case was evaluated"]
    return failed + not_evaluated + not_judged + empty
