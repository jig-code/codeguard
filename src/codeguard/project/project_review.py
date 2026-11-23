from dataclasses import dataclass
from typing import Self

from diskcache import Cache

from codeguard.config import GeminiSettings, Ruleset
from codeguard.pattern_rules import PatternRuleCheck
from codeguard.project.cache_directory import cache_directory
from codeguard.project.project import Project
from codeguard.project.provider_judges import ProviderJudges
from codeguard.project.ruleset_resolver import RulesetResolver
from codeguard.repository import ChangedLines, LineScope
from codeguard.review import (
    Bindings,
    CachedJudges,
    CheckStep,
    Deadline,
    JudgeCheck,
    JudgePlan,
    JudgeRequest,
    PlannedCall,
    Review,
    Reviewer,
)
from codeguard.syntax import ChangeClassifier, Classification


@dataclass(frozen=True)
class ProjectReview:
    project: Project
    rulesets: tuple[Ruleset, ...]
    judges: CachedJudges
    gemini: GeminiSettings

    @classmethod
    def of(cls, project: Project, skip_ci_only: bool = False) -> Self:
        gemini = GeminiSettings()
        return cls(
            project,
            RulesetResolver.of(project, skip_ci_only).rulesets,
            CachedJudges(
                ProviderJudges(project.config.judge, gemini), Cache(cache_directory("judgements"))
            ),
            gemini,
        )

    def review(self, scope: LineScope) -> Review:
        deadline = Deadline(self.project.config.review_time_limit_minutes)
        classification = self._classification(scope)
        bindings = self._bindings
        self.gemini.require_sign_in_for(binding.model for binding in bindings)
        root = self.project.root
        judge_checks = tuple(
            JudgeCheck(
                self.project.working_tree,
                binding,
                self.judges(root, binding.model, deadline),
                scope,
                classification,
            )
            for binding in bindings
        )
        reviewer = Reviewer(steps=(self._pattern_step, CheckStep(checks=judge_checks)))
        return reviewer.run(scope)

    def check_patterns(self, scope: LineScope) -> Review:
        return Reviewer(steps=(self._pattern_step,)).run(scope)

    def plan(self, scope: LineScope) -> JudgePlan:
        root = self.project.root
        classification = self._classification(scope)
        return JudgePlan(
            calls=tuple(
                PlannedCall(
                    rule=binding.rule,
                    file=file,
                    cached=self.judges(root, binding.model).has(
                        JudgeRequest.of_change(
                            binding, self.project.working_tree, file, scope, classification
                        )
                    ),
                    triggered=classification.is_triggered(file, binding.triggers),
                )
                for binding in self._bindings
                for file in binding.files(scope.files)
            )
        )

    @property
    def _bindings(self) -> Bindings:
        return Bindings.from_rulesets(self.rulesets, self.project.config.judge.choice)

    @property
    def _pattern_step(self) -> CheckStep:
        return CheckStep(
            checks=tuple(
                PatternRuleCheck(self.project.root, ruleset, self.project.ast_grep)
                for ruleset in self.rulesets
            )
        )

    def _classification(self, scope: LineScope) -> Classification:
        if not isinstance(scope, ChangedLines):
            return Classification()
        classifier = ChangeClassifier.for_rulesets(
            self.project.ast_grep, self.rulesets, self.project.working_tree
        )
        return classifier.classify(scope)
