from dataclasses import dataclass
from enum import StrEnum

from codeguard.config import ConfigError, RulesetLoader
from codeguard.rule_validation.judge_rule_file import JudgeRuleFile
from codeguard.rule_validation.validation_result import ValidationResult


class WhyValidationMode(StrEnum):
    WARN = "warn"
    FAIL = "fail"
    OFF = "off"

    def result(self, missing: tuple[str, ...]) -> ValidationResult:
        if self is WhyValidationMode.FAIL:
            return ValidationResult(problems=missing)
        if self is WhyValidationMode.WARN:
            return ValidationResult(warnings=missing)
        return ValidationResult()


@dataclass(frozen=True)
class WhyValidation:
    """Report each rule that doesn't say why it exists: a legacy skill's `## Why` section,
    a pattern rule's `metadata.why`. A rule nobody can trace to a reason can't be
    reviewed when the code or the design around it changes. A rule file bound with `rule`
    is held to this by RuleFormatValidation."""

    ruleset: RulesetLoader
    mode: WhyValidationMode = WhyValidationMode.WARN

    def run(self) -> ValidationResult:
        try:
            ruleset = self.ruleset.load()
        except ConfigError:
            # BroadTriggersValidation already reports an invalid ruleset.
            return ValidationResult()
        return self.mode.result(
            (
                *(
                    f"{rule_file.rule_id}: no ## Why section in its rule file"
                    for rule_file in JudgeRuleFile.from_ruleset(ruleset)
                    if rule_file.is_legacy_skill and not rule_file.outline.says_why
                ),
                *(
                    f"{rule.id}: no metadata.why"
                    for rule in sorted(ruleset.pattern_rules(), key=lambda rule: rule.id)
                    if not rule.says_why
                ),
            )
        )
