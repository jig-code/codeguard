from collections import defaultdict

from pydantic import ConfigDict, RootModel, field_validator

from codeguard.config.binding_config import BindingConfig


class BindingsConfig(RootModel[dict[str, BindingConfig]]):
    model_config = ConfigDict(frozen=True)

    @field_validator("root")
    @classmethod
    def validate_rules_bound_once(
        cls, bindings: dict[str, BindingConfig]
    ) -> dict[str, BindingConfig]:
        files: defaultdict[str, list[str]] = defaultdict(list)
        for file, binding in bindings.items():
            files[binding.rule_id].append(file)
        for rule, bound_in in files.items():
            if len(bound_in) > 1:
                raise ValueError(f"rule {rule} is bound more than once: {', '.join(bound_in)}")
        return bindings
