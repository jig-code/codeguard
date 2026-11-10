import factory

from codeguard.config import BindingConfig, BindingsConfig, Ruleset


class MakeBindingConfig(factory.Factory):
    class Meta:
        model = BindingConfig

    paths = ("**",)
    triggers = frozenset({"any"})


class MakeRuleset(factory.Factory):
    class Meta:
        model = Ruleset
        exclude = ("binding",)

    binding = factory.SubFactory(MakeBindingConfig)
    name = None
    root = factory.LazyAttribute(lambda ruleset: ruleset.binding.skill.parent)
    bindings = factory.LazyAttribute(
        lambda ruleset: BindingsConfig({"placement.yaml": ruleset.binding})
    )
