from dataclasses import dataclass

from codeguard.config import ChangeKind, ConfigError, RulesetLoader
from codeguard.rule_validation.rule_test_result import RuleTestResult

_BROAD = frozenset(
    {
        ChangeKind.ANY,
        ChangeKind.CODE,
        ChangeKind.FUNCTION_BODY,
        ChangeKind.FUNCTION_SIGNATURE,
    }
)


@dataclass(frozen=True)
class BroadTriggers:
    ruleset: RulesetLoader

    def run(self) -> RuleTestResult:
        try:
            bindings = self.ruleset.load().bindings.root.values()
        except ConfigError as error:
            return RuleTestResult(failed=False, warnings=(f"triggers not checked: {error}",))
        return RuleTestResult(
            failed=False,
            warnings=tuple(
                f"{binding.rule_id}: broad triggers {', '.join(sorted(broad))}; "
                "a gate on the code its violations need skips more files"
                for binding in sorted(bindings, key=lambda binding: binding.rule_id)
                if (broad := _BROAD & binding.triggers)
            ),
        )
