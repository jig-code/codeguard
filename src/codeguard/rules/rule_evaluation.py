from dataclasses import dataclass

from codeguard.config import JudgeModel
from codeguard.judge_evals import EvalCoverage, EvalSelection, JudgeEvalResult, JudgeEvalRunner
from codeguard.rule_tests import RuleTestResult
from codeguard.rules.rules import Rules


@dataclass(frozen=True)
class RuleEvaluation:
    rules: Rules

    def run(
        self,
        repeat: int = 1,
        selection: EvalSelection = EvalSelection(),
        model: JudgeModel | None = None,
    ) -> JudgeEvalResult:
        rules = self.rules
        root = rules.working_tree.root
        config = rules.config
        # An eval tests the rule, not the code, so each run calls the model: a cached
        # verdict says nothing about the rule as it is now.
        judge = rules.judges.uncached
        runners = [
            (
                loader,
                JudgeEvalRunner(
                    root,
                    loader,
                    judge,
                    config.confidence_threshold,
                    repeat,
                    config.judge,
                    rules.ast_grep,
                    selection,
                    model,
                ),
            )
            for loader in rules.resolver.own_rulesets
        ]
        if selection != EvalSelection():
            case_names: dict[str, tuple[str, ...]] = {}
            for _, runner in runners:
                for rule, cases in runner.case_names().items():
                    case_names[rule] = case_names.get(rule, ()) + cases
            problems = selection.problems(case_names)
            if problems:
                return JudgeEvalResult(checks=RuleTestResult(problems=problems))
        return JudgeEvalResult.merge(
            result
            for loader, runner in runners
            for result in (
                runner.run(),
                JudgeEvalResult(checks=EvalCoverage(loader, selection).run()),
            )
        )
