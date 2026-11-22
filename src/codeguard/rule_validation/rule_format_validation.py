from dataclasses import dataclass

from codeguard.config import ConfigError, RulesetLoader
from codeguard.rule_validation.judge_rule_file import JudgeRuleFile
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
                f"{rule_file.rule_id}: rule file {problem}"
                for rule_file in JudgeRuleFile.from_ruleset(ruleset)
                if not rule_file.is_legacy_skill
                for problem in rule_file.outline.format_problems()
            )
        )
