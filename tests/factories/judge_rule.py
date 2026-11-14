import factory

from codeguard.config import JudgeChoice
from codeguard.review import Binding, JudgeRule, Severity


class MakeJudgeRule(factory.Factory):
    class Meta:
        model = JudgeRule

    class Params:
        no_print = factory.Trait(name="no-print", text="# No print\n")

    name = "responsibility-placement"
    text = (
        "# Responsibility placement\n\nA method lives on the type whose data it reads.\n\n"
        "## Why\n\nLogic away from its data is missed when the data changes.\n"
    )


class MakeBinding(factory.Factory):
    class Meta:
        model = Binding

    rule = factory.LazyAttribute(lambda binding: binding.judge_rule.name)
    judge_rule = factory.SubFactory(MakeJudgeRule)
    paths = ("**",)
    severity = Severity.ERROR
    judge = JudgeChoice()
    triggers = frozenset({"any"})
