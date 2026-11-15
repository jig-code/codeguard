import factory

from codeguard.config import BindingConfig, BindingsConfig, Ruleset


class MakeBindingConfig(factory.Factory):
    class Meta:
        model = BindingConfig

    rule = "responsibility-placement"
    paths = ("**",)
    triggers = frozenset({"any"})


class MakeRuleset(factory.Factory):
    class Meta:
        model = Ruleset
        exclude = ("binding",)

    binding = factory.SubFactory(MakeBindingConfig)
    name = None
    bindings = factory.LazyAttribute(
        lambda ruleset: BindingsConfig({"placement.yaml": ruleset.binding})
    )
