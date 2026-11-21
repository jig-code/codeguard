from dataclasses import dataclass

from codeguard.config import EditVerdict, FileEdit, JudgedViolation, Outcome
from codeguard.judge_evals.judge_factory import JudgeFactory
from codeguard.repository import LineScopes, WorkingTree
from codeguard.review import Binding, JudgeRequest
from codeguard.syntax import ChangeClassifier, SyntaxScanner


@dataclass(frozen=True)
class EditReviewTask:
    binding: Binding
    judges: JudgeFactory
    scanner: SyntaxScanner

    def __call__(self, inputs: FileEdit) -> EditVerdict:
        if not self.binding.files([inputs.file]):
            return EditVerdict(outcome=Outcome.SKIPPED)
        with WorkingTree.temporary(inputs.before_files(), inputs.after_files()) as tree:
            changed = LineScopes.at(tree).changed_lines("HEAD")
            classification = ChangeClassifier(self.scanner, tree).classify(changed)
            if inputs.file not in changed.files or not classification.is_triggered(
                inputs.file, self.binding.triggers
            ):
                return EditVerdict(outcome=Outcome.SKIPPED)
            judge = self.judges(tree.root, self.binding.model)
            request = JudgeRequest.of_change(
                self.binding, tree, inputs.file, changed, classification
            )
            verdict = judge.judge(request).verdict
            parsed = self.scanner.scan_files(tree.root, [inputs.file]).get(inputs.file)
        violations = tuple(
            JudgedViolation(
                lines=violation.lines,
                message=violation.message,
                kinds=None if parsed is None else tuple(sorted(parsed.kinds_on(violation.lines))),
            )
            for violation in verdict.violations
            if changed.covers(violation.file, violation.lines) and violation.file == inputs.file
        )
        return EditVerdict(
            outcome=Outcome.INVALID if violations else Outcome.VALID,
            reason=verdict.reason,
            violations=violations,
        )
