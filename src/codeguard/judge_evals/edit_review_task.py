from dataclasses import dataclass

from codeguard.judge_evals.judge_factory import JudgeFactory
from codeguard.review import (
    Binding,
    Category,
    CheckStep,
    Diagnostic,
    JudgeCheck,
    JudgeError,
    JudgeNoVerdict,
    JudgeProcessError,
    JudgeTimeout,
    Reviewer,
)
from codeguard.rule_tests import EditCase, EditRepo, EditReview, JudgedViolation, Outcome
from codeguard.syntax import SyntaxScanner

_JUDGE_ERRORS = {
    error.error_type: error for error in (JudgeTimeout, JudgeProcessError, JudgeNoVerdict)
}


@dataclass(frozen=True)
class EditReviewTask:
    binding: Binding
    judges: JudgeFactory
    confidence_threshold: float
    scanner: SyntaxScanner

    # Judges the edit the way a review does, through the rule's JudgeCheck, so a case
    # passes only when a review would give the edit that outcome.
    def __call__(self, inputs: EditCase) -> EditReview:
        with EditRepo.of(inputs.edits()) as repo:
            changed = repo.classified(self.scanner)
            if inputs.file not in self.binding.triggered_files(changed, changed.files):
                return EditReview(outcome=Outcome.SKIPPED)
            check = JudgeCheck(
                repo.root,
                self.binding,
                self.judges(repo.root, self.binding.model),
                self.confidence_threshold,
                changed,
            )
            review = Reviewer(steps=(CheckStep(checks=(check,)),)).run(changed)
            parsed = self.scanner.scan_files(repo.root, [inputs.file]).get(inputs.file)
        for diagnostic in review.diagnostics:
            _raise_judge_error(diagnostic)
        violations = tuple(
            JudgedViolation(
                line=diagnostic.line,
                confidence=diagnostic.confidence,
                message=diagnostic.message,
                kinds=None if parsed is None else tuple(sorted(parsed.kinds_on(diagnostic.line))),
            )
            for diagnostic in review.diagnostics
            if diagnostic.file == inputs.file and diagnostic.line is not None
        )
        return EditReview(outcome=self._outcome(violations), violations=violations)

    def _outcome(self, violations: tuple[JudgedViolation, ...]) -> Outcome:
        if any(violation.confidence >= self.confidence_threshold for violation in violations):
            return Outcome.INVALID
        return Outcome.UNCERTAIN if violations else Outcome.VALID


def _raise_judge_error(diagnostic: Diagnostic) -> None:
    if diagnostic.category is Category.JUDGE_ERROR and diagnostic.error_type is not None:
        error: type[JudgeError] = _JUDGE_ERRORS[diagnostic.error_type]
        raise error(diagnostic.note)
