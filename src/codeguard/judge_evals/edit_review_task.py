from dataclasses import dataclass

from codeguard.judge_evals.judge_factory import JudgeFactory
from codeguard.review import Binding, JudgeRequest
from codeguard.rule_tests import EditCase, EditRepo, EditReview, JudgedViolation, Outcome
from codeguard.syntax import SyntaxScanner


@dataclass(frozen=True)
class EditReviewTask:
    binding: Binding
    judges: JudgeFactory
    confidence_threshold: float
    scanner: SyntaxScanner

    def __call__(self, inputs: EditCase) -> EditReview:
        if not self.binding.files([inputs.file]):
            return EditReview(outcome=Outcome.SKIPPED)
        with EditRepo.of(inputs.edits()) as repo:
            changed = repo.changed_lines()
            classification = repo.classification(self.scanner, changed)
            if inputs.file not in changed.files or not classification.is_triggered(
                inputs.file, self.binding.triggers
            ):
                return EditReview(outcome=Outcome.SKIPPED)
            judge = self.judges(repo.root, self.binding.model)
            request = JudgeRequest.of_change(
                self.binding, repo.root, inputs.file, changed, classification
            )
            verdict = judge.judge(request).verdict
            parsed = self.scanner.scan_files(repo.root, [inputs.file]).get(inputs.file)
        violations = tuple(
            JudgedViolation(
                lines=violation.lines,
                confidence=violation.confidence,
                message=violation.message,
                kinds=None if parsed is None else tuple(sorted(parsed.kinds_on(violation.lines))),
            )
            for violation in verdict.violations
            if changed.covers(violation.file, violation.lines) and violation.file == inputs.file
        )
        return EditReview(
            outcome=self._outcome(violations), reason=verdict.reason, violations=violations
        )

    def _outcome(self, violations: tuple[JudgedViolation, ...]) -> Outcome:
        if any(violation.confidence >= self.confidence_threshold for violation in violations):
            return Outcome.INVALID
        return Outcome.UNCERTAIN if violations else Outcome.VALID
