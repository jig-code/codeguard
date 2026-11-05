from dataclasses import dataclass, replace
from functools import cached_property

from codeguard.ast_grep import AstGrep
from codeguard.config import Config, ConfigLoader, Ruleset
from codeguard.pattern_rules import Layout, PatternRuleCheck, PatternRuleTestRunner
from codeguard.review import (
    Bindings,
    CheckStep,
    Deadline,
    JudgeCheck,
    JudgePlan,
    JudgeRequest,
    PlannedCall,
    Review,
    Reviewer,
)
from codeguard.rule_tests import (
    BroadTriggers,
    MissingWhy,
    MissingWhyMode,
    RuleTests,
    TriggerTestRunner,
)
from codeguard.rules.judges import Judges
from codeguard.rules.ruleset_resolver import RulesetResolver
from codeguard.syntax import ChangeClassifier
from codeguard.working_tree import AllLines, ChangedLines, WorkingTree


@dataclass(frozen=True)
class Rules:
    working_tree: WorkingTree
    skip_ci_only: bool = False

    @cached_property
    def config(self) -> Config:
        return ConfigLoader(self.working_tree.root).load()

    def review(self, scope: ChangedLines | AllLines) -> Review:
        deadline = Deadline(self.config.review_time_limit_minutes)
        classified = self._classified(scope)
        reviewer = Reviewer(
            steps=(
                self._pattern_step,
                CheckStep(checks=self._judge_checks(classified, deadline)),
            )
        )
        return reviewer.run(classified)

    def check_patterns(self, scope: ChangedLines | AllLines) -> Review:
        return Reviewer(steps=(self._pattern_step,)).run(scope)

    @property
    def _pattern_step(self) -> CheckStep:
        root = self.working_tree.root
        return CheckStep(
            checks=tuple(
                PatternRuleCheck(root, ruleset, self.ast_grep) for ruleset in self.rulesets
            )
        )

    def _classified(self, scope: ChangedLines | AllLines) -> ChangedLines | AllLines:
        if isinstance(scope, AllLines):
            return scope
        classifier = ChangeClassifier.for_rulesets(self.ast_grep, self.rulesets, self.working_tree)
        return classifier.classify(scope)

    def plan(self, scope: ChangedLines | AllLines) -> JudgePlan:
        root = self.working_tree.root
        classified = self._classified(scope)
        return JudgePlan(
            calls=tuple(
                PlannedCall(
                    rule=binding.rule,
                    file=file,
                    cached=self.judges.cached(root, binding.model, probe=False).has(
                        JudgeRequest.of_change(binding, root, file, classified)
                    ),
                    triggered=binding.is_triggered(classified, file),
                )
                for binding in Bindings.from_rulesets(self.rulesets, self.config.judge.choice)
                for file in binding.files(classified.files)
            )
        )

    def tests(self, missing_why: MissingWhyMode = MissingWhyMode.WARN) -> RuleTests:
        root = self.working_tree.root
        loaders = self.resolver.own_rulesets
        return RuleTests(
            snapshot_runners=[
                PatternRuleTestRunner(Layout(root, loader.root, self.ast_grep))
                for loader in loaders
            ],
            runners=[
                runner
                for loader in loaders
                for runner in (
                    BroadTriggers(loader),
                    TriggerTestRunner(root, loader, self.ast_grep),
                    MissingWhy(loader, missing_why),
                )
            ],
        )

    @cached_property
    def ast_grep(self) -> AstGrep:
        ast_grep = AstGrep(self.config.ast_grep)
        ast_grep.check_supported()
        return ast_grep

    @cached_property
    def resolver(self) -> RulesetResolver:
        return RulesetResolver(self.working_tree.root, self.config, self.ast_grep)

    @cached_property
    def rulesets(self) -> tuple[Ruleset, ...]:
        """The rulesets a review runs."""
        return tuple(
            replace(ruleset, skip_ci_only=self.skip_ci_only) for ruleset in self.resolver.rulesets
        )

    @cached_property
    def judges(self) -> Judges:
        return Judges(self.config.judge)

    def _judge_checks(
        self, scope: ChangedLines | AllLines, deadline: Deadline
    ) -> tuple[JudgeCheck, ...]:
        root = self.working_tree.root
        threshold = self.config.confidence_threshold
        return tuple(
            JudgeCheck(
                root, binding, self.judges.cached(root, binding.model, deadline), threshold, scope
            )
            for binding in Bindings.from_rulesets(self.rulesets, self.config.judge.choice)
        )
