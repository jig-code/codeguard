from dataclasses import dataclass

from codeguard.config import ChangeKind, ConfigError, RulesetLoader
from codeguard.rule_validation.validation_result import ValidationResult

_BROAD = frozenset(
    {
        ChangeKind.ANY,
        ChangeKind.CODE,
        ChangeKind.FUNCTION_BODY,
        ChangeKind.FUNCTION_SIGNATURE,
    }
)


@dataclass(frozen=True)
class BroadTriggersValidation:
    ruleset: RulesetLoader

    def run(self) -> ValidationResult:
        try:
            bindings = self.ruleset.load().bindings.root.values()
        except ConfigError as error:
            return ValidationResult(failed=False, warnings=(f"triggers not checked: {error}",))
        return ValidationResult(
            failed=False,
            warnings=tuple(
                f"{binding.rule_id}: broad triggers {', '.join(sorted(broad))}; "
                "a gate on the code its violations need skips more files"
                for binding in sorted(bindings, key=lambda binding: binding.rule_id)
                if (broad := _BROAD & binding.triggers)
            ),
        )
