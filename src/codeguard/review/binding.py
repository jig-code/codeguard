import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Self

from codeguard.config import (
    SKILL_FILE,
    BindingConfig,
    JudgeChoice,
    JudgeModel,
    PathScope,
    Ruleset,
    Severity,
    language_of,
    named_languages,
)
from codeguard.review.skill import Skill


@dataclass(frozen=True)
class Binding:
    rule: str
    skill: Skill
    paths: tuple[str, ...]
    severity: Severity
    triggers: frozenset[str]
    judge: JudgeChoice = JudgeChoice()
    exclude_paths: tuple[str, ...] = ()
    supplements: Mapping[str, Skill] = field(default_factory=dict, hash=False)

    @classmethod
    def from_config(cls, rule: str, binding: BindingConfig, judge: JudgeChoice) -> Self:
        return cls(
            rule=rule,
            skill=Skill.from_file(binding.skill.name, binding.skill / SKILL_FILE),
            paths=binding.paths,
            severity=binding.severity,
            judge=judge,
            triggers=binding.triggers,
            exclude_paths=binding.exclude_paths,
            supplements={
                language: Skill.from_file(binding.skill.name, file)
                for language, file in binding.supplements.items()
            },
        )

    @property
    def model(self) -> JudgeModel:
        return self.judge.judge_model

    @property
    def languages(self) -> frozenset[str]:
        return named_languages(self.paths)

    def skill_for(self, file: str) -> Skill:
        return self._skill_in(language_of(file))

    def version_for(self, language: str | None) -> str:
        """Identify what decides the rule's verdicts in a language, other than its model."""
        texts = (
            [self._skill_in(language).text]
            if language
            else [
                self.skill.text,
                *(self.supplements[name].text for name in sorted(self.supplements)),
            ]
        )
        rule = [texts, sorted(self.triggers), self.paths, self.exclude_paths]
        return hashlib.sha256(json.dumps(rule).encode()).hexdigest()[:12]

    def _skill_in(self, language: str | None) -> Skill:
        supplement = self.supplements.get(language) if language else None
        if supplement is None:
            return self.skill
        return Skill(name=self.skill.name, text=f"{self.skill.text}\n{supplement.text}")

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
                judge_override
                if judge_override.provider
                else binding.judge.over(project_judge).over(ruleset.package_judge),
            )
            for ruleset in rulesets
            for rule, binding in ruleset.selected_bindings().items()
        )
