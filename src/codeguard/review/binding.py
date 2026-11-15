import hashlib
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Self

from codeguard.config import (
    BindingConfig,
    JudgeChoice,
    JudgeModel,
    PathScope,
    Ruleset,
    Severity,
    named_languages,
)
from codeguard.review.judge_rule import JudgeRule


@dataclass(frozen=True)
class Binding:
    rule: str
    judge_rule: JudgeRule
    paths: tuple[str, ...]
    severity: Severity
    triggers: frozenset[str]
    judge: JudgeChoice = JudgeChoice()
    exclude_paths: tuple[str, ...] = ()

    @classmethod
    def from_config(
        cls, rule: str, binding: BindingConfig, judge_rule: JudgeRule, judge: JudgeChoice
    ) -> Self:
        return cls(
            rule=rule,
            judge_rule=judge_rule,
            paths=binding.paths,
            severity=binding.severity,
            judge=judge,
            triggers=binding.triggers,
            exclude_paths=binding.exclude_paths,
        )

    @property
    def model(self) -> JudgeModel:
        return self.judge.judge_model

    @property
    def languages(self) -> frozenset[str]:
        return named_languages(self.paths)

    @property
    def version(self) -> str:
        """Identify what decides the rule's verdicts, other than its model."""
        rule = [self.judge_rule.text, sorted(self.triggers), self.paths, self.exclude_paths]
        return hashlib.sha256(json.dumps(rule).encode()).hexdigest()[:12]

    def files(self, changed: Sequence[str]) -> list[str]:
        return [file for file in changed if self._matches(file)]

    def _matches(self, file: str) -> bool:
        return PathScope(self.paths, self.exclude_paths).matches(file)


class Bindings(tuple[Binding, ...]):
    @classmethod
    def from_rulesets(
        cls,
        rulesets: Iterable[Ruleset],
        project_judge: JudgeChoice = JudgeChoice(),
        judge_override: JudgeChoice = JudgeChoice(),
    ) -> Self:
        return cls(
            Binding.from_config(
                rule,
                binding,
                JudgeRule(name=binding.rule_id, text=ruleset.judge_rule_text(binding)),
                judge_override
                if judge_override.provider
                else binding.judge.over(project_judge).over(ruleset.package_judge),
            )
            for ruleset in rulesets
            for rule, binding in ruleset.selected_bindings().items()
        )
