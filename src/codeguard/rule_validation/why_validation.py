from dataclasses import dataclass
from enum import StrEnum

from codeguard.config import ConfigError, RulesetLoader
from codeguard.review import Bindings
from codeguard.rule_validation.rule_test_result import RuleTestResult


class WhyValidationMode(StrEnum):
    WARN = "warn"
    FAIL = "fail"
    OFF = "off"

    def result(self, missing: tuple[str, ...]) -> RuleTestResult:
        if self is WhyValidationMode.FAIL:
            return RuleTestResult(problems=missing)
        if self is WhyValidationMode.WARN:
            return RuleTestResult(warnings=missing)
        return RuleTestResult()


@dataclass(frozen=True)
class WhyValidation:
    """Report each rule that doesn't say why it exists: a judge rule's `## Why` section,
    a pattern rule's `metadata.why`. A rule nobody can trace to a reason can't be
    reviewed when the code or the design around it changes."""

    ruleset: RulesetLoader
    mode: WhyValidationMode = WhyValidationMode.WARN

    def run(self) -> RuleTestResult:
        try:
            ruleset = self.ruleset.load()
        except ConfigError:
            # BroadTriggers already reports an invalid ruleset.
            return RuleTestResult()
        judge_rules = (binding.judge_rule for binding in Bindings.from_rulesets([ruleset]))
        return self.mode.result(
            (
                *(
                    f"{rule.name}: no ## Why section in its rule file"
                    for rule in sorted(judge_rules, key=lambda rule: rule.name)
                    if not rule.says_why
                ),
                *(
                    f"{rule.id}: no metadata.why"
                    for rule in sorted(ruleset.pattern_rules(), key=lambda rule: rule.id)
                    if not rule.says_why
                ),
            )
        )
