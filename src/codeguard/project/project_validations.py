from collections.abc import Sequence
from dataclasses import dataclass
from typing import Self

from codeguard.config import RulesetLoader
from codeguard.pattern_rules import Layout, PatternRuleValidation
from codeguard.project.project import Project
from codeguard.project.ruleset_resolver import RulesetResolver
from codeguard.rule_validation import (
    BroadTriggersValidation,
    RuleFormatValidation,
    RuleValidations,
    TriggerCaseValidation,
    WhyValidation,
    WhyValidationMode,
)


@dataclass(frozen=True)
class ProjectValidations:
    project: Project
    rulesets: Sequence[RulesetLoader]

    @classmethod
    def of(cls, project: Project) -> Self:
        return cls(project, RulesetResolver.of(project).own_rulesets)

    def validations(
        self, missing_why: WhyValidationMode = WhyValidationMode.WARN
    ) -> RuleValidations:
        root = self.project.root
        ast_grep = self.project.ast_grep
        return RuleValidations(
            snapshot_validations=[
                PatternRuleValidation(Layout(root, loader.root, ast_grep))
                for loader in self.rulesets
            ],
            validations=[
                validation
                for loader in self.rulesets
                for validation in (
                    BroadTriggersValidation(loader),
                    RuleFormatValidation(loader),
                    TriggerCaseValidation(root, loader, ast_grep),
                    WhyValidation(loader, missing_why),
                )
            ],
        )
