from dataclasses import dataclass

from codeguard.config import Outcome, RulesetLoader, rule_evals
from codeguard.judge_evals.eval_selection import EvalSelection
from codeguard.review import Bindings
from codeguard.rule_validation import RuleTestResult


@dataclass(frozen=True)
class EvalCoverage:
    ruleset: RulesetLoader
    selection: EvalSelection = EvalSelection()

    def run(self) -> RuleTestResult:
        ruleset = self.ruleset.load()
        bindings = Bindings.from_rulesets([ruleset])
        languages = {binding.judge_rule.name: binding.languages for binding in bindings}
        evaluated = {
            part.name
            for _, dataset in rule_evals(ruleset.root)
            for _, part in dataset.by_language(languages.get(dataset.name, frozenset()))
            if any(
                case.expected_output and case.expected_output.outcome is Outcome.INVALID
                for case in part.cases
            )
        }
        # A rule whose paths name several languages needs an invalid case in each.
        return RuleTestResult(
            problems=tuple(
                f"{name}: no eval with an invalid case"
                for binding in bindings
                if self.selection.selects_rule(binding.judge_rule.name)
                for name in _names(binding.judge_rule.name, binding.languages)
                if name not in evaluated
            )
        )


def _names(rule: str, languages: frozenset[str]) -> list[str]:
    if len(languages) < 2:
        return [rule]
    return [f"{rule} ({language})" for language in sorted(languages)]
