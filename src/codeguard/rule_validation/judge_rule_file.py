from dataclasses import dataclass
from typing import Self

from codeguard.config import Ruleset
from codeguard.rule_validation.rule_file_outline import RuleFileOutline


@dataclass(frozen=True)
class JudgeRuleFile:
    rule_id: str
    is_legacy_skill: bool
    outline: RuleFileOutline

    @classmethod
    def from_ruleset(cls, ruleset: Ruleset) -> tuple[Self, ...]:
        return tuple(
            cls(
                rule_id=binding.rule_id,
                is_legacy_skill=binding.is_legacy_skill,
                outline=RuleFileOutline.from_text(ruleset.judge_rule_text(binding)),
            )
            for binding in sorted(
                ruleset.selected_bindings().values(), key=lambda binding: binding.rule_id
            )
        )
