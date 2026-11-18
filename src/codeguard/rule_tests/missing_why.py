from dataclasses import dataclass
from enum import StrEnum

from codeguard.config import ConfigError, RulesetLoader
from codeguard.review import Bindings
from codeguard.rule_tests.rule_test_result import RuleTestResult


class MissingWhyMode(StrEnum):
    WARN = "warn"
    FAIL = "fail"
    OFF = "off"

    def result(self, missing: tuple[str, ...]) -> RuleTestResult:
        if self is MissingWhyMode.FAIL:
            return RuleTestResult(problems=missing)
        if self is MissingWhyMode.WARN:
            return RuleTestResult(warnings=missing)
        return RuleTestResult()


@dataclass(frozen=True)
class MissingWhy:
    """Report each rule that doesn't say why it exists: a judge rule's `## Why` section,
    a pattern rule's `metadata.why`. A rule nobody can trace to a reason can't be
    reviewed when the code or the design around it changes."""

    ruleset: RulesetLoader
    mode: MissingWhyMode = MissingWhyMode.WARN

    def run(self) -> RuleTestResult:
        try:
            ruleset = self.ruleset.load()
        except ConfigError:
            # BroadTriggers already reports an invalid ruleset.
            return RuleTestResult()
        judge_rules = sorted(
            (binding.judge_rule for binding in Bindings.from_rulesets([ruleset])),
            key=lambda rule: rule.name,
        )
        pattern_rules = sorted(ruleset.pattern_rules(), key=lambda rule: rule.id)
        return self.mode.result(
            (
                *(
                    f"{rule.name}: no ## Why section in its rule file"
                    for rule in judge_rules
                    if not rule.says_why
                ),
                *(f"{rule.id}: no metadata.why" for rule in pattern_rules if not rule.says_why),
            )
        )
