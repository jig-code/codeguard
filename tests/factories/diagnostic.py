import factory

from codeguard.review import Category, Diagnostic, ErrorType, Severity
from codeguard.review.judge import Violation
from factories.judge_rule import MakeJudgeRule
from factories.line_range import MakeLineRange


class MakeDiagnostic(factory.Factory):
    class Meta:
        model = Diagnostic

    class Params:
        warning = factory.Trait(
            rule="no-breakpoint",
            message="Remove breakpoint().",
            severity=Severity.WARNING,
            note=None,
        )
        judged = factory.Trait(
            rule=factory.LazyFunction(lambda: MakeJudgeRule().name),
            note=None,
            category=Category.JUDGED,
        )
        judge_error = factory.Trait(
            rule=factory.LazyFunction(lambda: MakeJudgeRule().name),
            lines=None,
            message="The judge call failed, so this rule was not checked.",
            note="claude exited with 1.",
            category=Category.JUDGE_ERROR,
            error_type=ErrorType.PROCESS,
        )

    rule = "no-print"
    file = "a.py"
    lines = factory.SubFactory(MakeLineRange)
    message = "Use logging, not print."
    severity = Severity.ERROR
    note = "print bypasses log levels.\nCall logger.info instead.\n"
    category = Category.PATTERN
    error_type = None


class MakeViolation(factory.Factory):
    class Meta:
        model = Violation

    file = "a.py"
    lines = factory.SubFactory(MakeLineRange)
    message = "Use logging, not print."
