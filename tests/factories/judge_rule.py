import factory

from codeguard.config import JudgeChoice
from codeguard.review import Binding, Severity, Skill


class MakeSkill(factory.Factory):
    class Meta:
        model = Skill

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

    rule = factory.LazyAttribute(lambda binding: binding.skill.name)
    skill = factory.SubFactory(MakeSkill)
    paths = ("**",)
    severity = Severity.ERROR
    judge = JudgeChoice()
    triggers = frozenset({"any"})
