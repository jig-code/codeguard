import factory
from pydantic_evals.evaluators import EvaluatorContext
from pydantic_evals.otel import SpanTree

from codeguard.config import EditVerdict, FileEdit, JudgedViolation, Outcome, RuleEvalCase
from codeguard.review import Verdict
from factories.line_range import MakeLineRange


class MakeVerdict(factory.Factory):
    class Meta:
        model = Verdict

    class Params:
        breaking = factory.Trait(reason="The code breaks the convention.")

    reason = "The code keeps the convention."
    violations = ()


class MakeFileEdit(factory.Factory):
    class Meta:
        model = FileEdit

    file = "module.py"
    after = "ship(status='shipped')\n"


class MakeJudgedViolation(factory.Factory):
    class Meta:
        model = JudgedViolation

    lines = factory.SubFactory(MakeLineRange)
    message = "Pass the member."


class MakeEditVerdict(factory.Factory):
    class Meta:
        model = EditVerdict

    outcome = Outcome.INVALID


class MakeEvaluatorContext(factory.Factory):
    class Meta:
        model = EvaluatorContext

    name = "a string"
    inputs = factory.SubFactory(MakeFileEdit)
    metadata = None
    expected_output = factory.SubFactory(MakeEditVerdict)
    output = factory.SubFactory(MakeEditVerdict)
    duration = 0.0
    _span_tree = factory.LazyFunction(SpanTree)
    attributes = factory.LazyFunction(dict)
    metrics = factory.LazyFunction(dict)


class MakeRuleEvalCase(factory.Factory):
    class Meta:
        model = RuleEvalCase

    name = "a string"
    inputs = factory.SubFactory(MakeFileEdit)
    expected_output = factory.SubFactory(MakeEditVerdict, outcome=Outcome.VALID)
