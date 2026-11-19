from dataclasses import dataclass

from codeguard.config import ConfigError, RulesetLoader
from codeguard.review import JudgeRule
from codeguard.rule_validation.validation_result import ValidationResult


@dataclass(frozen=True)
class RuleFormatValidation:
    """Report each judge rule file that isn't a title, a statement and `## Why`. Rules
    bound with the legacy `skill` key are not checked: packages still ship them."""

    ruleset: RulesetLoader

    def run(self) -> ValidationResult:
        try:
            ruleset = self.ruleset.load()
        except ConfigError:
            # BroadTriggersValidation already reports an invalid ruleset.
            return ValidationResult()
        rules = sorted(
            (
                JudgeRule(binding.rule_id, ruleset.judge_rule_text(binding))
                for binding in ruleset.bindings.root.values()
                if binding.skill is None
            ),
            key=lambda rule: rule.name,
        )
        return ValidationResult(
            problems=tuple(
                f"{rule.name}: rule file {problem}"
                for rule in rules
                for problem in rule.format_problems()
            )
        )
