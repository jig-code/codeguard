from collections.abc import Sequence
from dataclasses import dataclass
from typing import Self

from codeguard.config import GeminiSettings, JudgeChoice, RulesetLoader
from codeguard.judge_evals import EvalCoverage, EvalSelection, JudgeEvalResult, JudgeEvalRunner
from codeguard.project.project import Project
from codeguard.project.provider_judges import ProviderJudges
from codeguard.project.ruleset_resolver import RulesetResolver
from codeguard.review import JudgeFactory
from codeguard.rule_validation import ValidationResult


@dataclass(frozen=True)
class RuleEvaluation:
    project: Project
    rulesets: Sequence[RulesetLoader]
    judges: JudgeFactory
    gemini: GeminiSettings

    @classmethod
    def of(cls, project: Project) -> Self:
        gemini = GeminiSettings()
        # An eval tests the rule, not the code, so each run calls the model: a cached verdict
        # says nothing about the rule as it is now.
        return cls(
            project,
            RulesetResolver.of(project).own_rulesets,
            ProviderJudges(project.config.judge, gemini),
            gemini,
        )

    def run(
        self,
        repeat: int = 1,
        selection: EvalSelection = EvalSelection(),
        judge_override: JudgeChoice = JudgeChoice(),
    ) -> JudgeEvalResult:
        runners = [
            (
                loader,
                JudgeEvalRunner(
                    self.project.root,
                    loader,
                    self.judges,
                    repeat,
                    self.project.config.judge,
                    self.project.ast_grep,
                    selection,
                    judge_override,
                ),
            )
            for loader in self.rulesets
        ]
        if selection != EvalSelection():
            case_names: dict[str, tuple[str, ...]] = {}
            for _, runner in runners:
                for rule, cases in runner.case_names().items():
                    case_names[rule] = case_names.get(rule, ()) + cases
            problems = selection.problems(case_names)
            if problems:
                return JudgeEvalResult(checks=ValidationResult(problems=problems))
        self.gemini.require_sign_in_for(
            model for _, runner in runners for model in runner.judge_models()
        )
        return JudgeEvalResult.merge(
            result
            for loader, runner in runners
            for result in (
                runner.run(),
                JudgeEvalResult(checks=EvalCoverage(loader, selection).run()),
            )
        )
