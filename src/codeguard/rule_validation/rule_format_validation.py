from dataclasses import dataclass

from codeguard.config import ConfigError, RulesetLoader
from codeguard.review import JudgeRule
from codeguard.rule_validation.validation_result import ValidationResult


@dataclass(frozen=True)
class RuleFormatValidation:
    """Skips rules bound with the legacy `skill` key, which packages still ship."""

    ruleset: RulesetLoader

    def run(self) -> ValidationResult:
        try:
            ruleset = self.ruleset.load()
        except ConfigError:
            # BroadTriggersValidation already reports an invalid ruleset.
            return ValidationResult()
        return ValidationResult(
            problems=tuple(
                f"{rule.name}: rule file {problem}"
                for rule in JudgeRule.rule_files_of(ruleset)
                for problem in rule.format_problems()
            )
        )
