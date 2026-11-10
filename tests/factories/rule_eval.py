import factory
from pydantic_evals.evaluators import EvaluatorContext
from pydantic_evals.otel import SpanTree

from codeguard.review import Verdict
from codeguard.rule_tests import EditCase, EditReview, JudgedViolation, Outcome, RuleEvalCase
from factories.line_range import MakeLineRange


class MakeVerdict(factory.Factory):
    class Meta:
        model = Verdict

    class Params:
        breaking = factory.Trait(reason="The code breaks the convention.")

    reason = "The code keeps the convention."
    violations = ()


class MakeEditCase(factory.Factory):
    class Meta:
        model = EditCase

    file = "module.py"
    after = "ship(status='shipped')\n"


class MakeJudgedViolation(factory.Factory):
    class Meta:
        model = JudgedViolation

    lines = factory.SubFactory(MakeLineRange)
    confidence = 0.9
    message = "Pass the member."


class MakeEditReview(factory.Factory):
    class Meta:
        model = EditReview

    outcome = Outcome.INVALID


class MakeEvaluatorContext(factory.Factory):
    class Meta:
        model = EvaluatorContext

    name = "a string"
    inputs = factory.SubFactory(MakeEditCase)
    metadata = None
    expected_output = factory.SubFactory(MakeEditReview)
    output = factory.SubFactory(MakeEditReview)
    duration = 0.0
    _span_tree = factory.LazyFunction(SpanTree)
    attributes = factory.LazyFunction(dict)
    metrics = factory.LazyFunction(dict)


class MakeRuleEvalCase(factory.Factory):
    class Meta:
        model = RuleEvalCase

    name = "a string"
    inputs = factory.SubFactory(MakeEditCase)
    expected_output = factory.SubFactory(MakeEditReview, outcome=Outcome.VALID)
