import asyncio
from dataclasses import dataclass
from importlib.metadata import version
from os import process_cpu_count
from pathlib import Path

from pydantic_evals import Case, Dataset

from codeguard.ast_grep import AstGrep
from codeguard.config import JudgeChoice, JudgeConfig, JudgeModel, Ruleset, RulesetLoader
from codeguard.judge_evals.edit_evaluators import PartialEqualsExpected, ViolationsOnTriggers
from codeguard.judge_evals.edit_review_task import EditReviewTask
from codeguard.judge_evals.eval_selection import EvalSelection
from codeguard.judge_evals.judge_eval_result import JudgeEvalResult, RuleEvalReport
from codeguard.judge_evals.judge_factory import JudgeFactory
from codeguard.review import Binding, Bindings
from codeguard.rule_tests import EditCase, EditReview, RuleEval, RuleTestResult, rule_evals
from codeguard.syntax import SyntaxScanner


@dataclass(frozen=True)
class JudgeEvalRunner:
    root: Path
    ruleset: RulesetLoader
    judges: JudgeFactory
    confidence_threshold: float
    repeat: int = 1
    judge_config: JudgeConfig = JudgeConfig()
    ast_grep: AstGrep = AstGrep()
    selection: EvalSelection = EvalSelection()
    judge_override: JudgeChoice = JudgeChoice()

    def case_names(self) -> dict[str, tuple[str, ...]]:
        cases = {dataset.name: dataset.cases for _, dataset in rule_evals(self.ruleset.root)}
        return {
            binding.skill.name: tuple(case.name for case in cases.get(binding.skill.name, ()))
            for binding in Bindings.from_rulesets(
                [self.ruleset.load()], self.judge_config.choice, self.judge_override
            )
        }

    def judge_models(self) -> tuple[JudgeModel, ...]:
        bindings = self._bindings(self.ruleset.load())
        return tuple(
            bindings[dataset.name].model
            for _, dataset in self._selected_evals()
            if dataset.name in bindings
        )

    def run(self) -> JudgeEvalResult:
        evals = self._selected_evals()
        if not evals:
            return JudgeEvalResult()
        ruleset = self.ruleset.load()
        bindings = self._bindings(ruleset)
        unknown = tuple(
            f"{file.relative_to(self.root)}: no judge rule {dataset.name}"
            for file, dataset in evals
            if dataset.name not in bindings
        )
        experiments = [
            (part, bindings[dataset.name], language)
            for _, dataset in evals
            if dataset.name in bindings
            for language, part in dataset.by_language(bindings[dataset.name].languages)
        ]
        scanner = SyntaxScanner.for_rulesets(self.ast_grep, [ruleset])
        reports = asyncio.run(self._evaluate_all(experiments, scanner))
        return JudgeEvalResult(reports=tuple(reports), checks=RuleTestResult(problems=unknown))

    def _selected_evals(self) -> list[tuple[Path, RuleEval]]:
        evals = [
            (file, self._selected_cases(dataset))
            for file, dataset in rule_evals(self.ruleset.root)
            if self.selection.selects_rule(dataset.name)
        ]
        if self.selection.cases:
            return [(file, dataset) for file, dataset in evals if dataset.cases]
        return evals

    def _bindings(self, ruleset: Ruleset) -> dict[str, Binding]:
        return {
            binding.skill.name: binding
            for binding in Bindings.from_rulesets(
                [ruleset], self.judge_config.choice, self.judge_override
            )
        }

    def _selected_cases(self, rule_eval: RuleEval) -> RuleEval:
        cases = tuple(case for case in rule_eval.cases if self.selection.selects_case(case.name))
        return rule_eval.model_copy(update={"cases": cases})

    async def _evaluate_all(
        self, experiments: list[tuple[RuleEval, Binding, str | None]], scanner: SyntaxScanner
    ) -> list[RuleEvalReport]:
        return await asyncio.gather(
            *(
                self._evaluate(dataset, binding, language, scanner)
                for dataset, binding, language in experiments
            )
        )

    async def _evaluate(
        self, rule_eval: RuleEval, binding: Binding, language: str | None, scanner: SyntaxScanner
    ) -> RuleEvalReport:
        model = binding.model
        dataset = Dataset[EditCase, EditReview, None](
            name=rule_eval.name,
            cases=[
                Case(name=case.name, inputs=case.inputs, expected_output=case.expected_output)
                for case in rule_eval.cases
            ],
            evaluators=[
                PartialEqualsExpected(),
                ViolationsOnTriggers(tuple(sorted(binding.triggers)), self.confidence_threshold),
            ],
        )
        task = EditReviewTask(binding, self.judges, self.confidence_threshold, scanner)
        return await dataset.evaluate(
            task,
            name=f"{dataset.name} on {model.label}",
            task_name=model.label,
            metadata={
                "provider": model.provider,
                "model": model.name,
                "confidence_threshold": self.confidence_threshold,
                "rule_version": binding.version_for(language),
                "codeguard_version": version("codeguard"),
            },
            repeat=self.repeat,
            max_concurrency=self.judge_config.concurrency(model.provider, process_cpu_count()),
            progress=False,
        )
