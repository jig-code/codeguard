from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from codeguard.ast_grep import AstGrep
from codeguard.config import ChangeKind, ConfigError, Ruleset, RulesetLoader
from codeguard.repository import ChangedLines
from codeguard.review import Binding, Bindings
from codeguard.rule_tests.edit_repo import EditRepo
from codeguard.rule_tests.rule_eval import Outcome, RuleEvalCase, rule_evals
from codeguard.rule_tests.rule_test_result import RuleTestResult
from codeguard.syntax import SyntaxScanner


@dataclass(frozen=True)
class _CaseCheck:
    binding: Binding
    case: RuleEvalCase
    name: str
    prefix: str

    @property
    def path(self) -> str:
        return f"{self.prefix}{self.case.inputs.file}"

    def problem(self, changed: ChangedLines) -> str | None:
        rule = self.binding.skill.name
        file = self.case.inputs.file
        expected = self.case.expected_output
        if not self.binding.files([file]):
            return f"{self.name}: {file} is outside the {rule} paths"
        if self.path not in changed.files:
            return f"{self.name}: the case changes no code in {file}"
        should_fire = expected.outcome is not Outcome.SKIPPED
        if self.binding.is_triggered(changed, self.path) == should_fire:
            return None
        kinds = changed.kinds_of(self.path)
        if kinds is None:
            # As in a review, a change in a language without change kinds fires every trigger.
            return f"{self.name}: {file} has no change kinds, so every {rule} trigger fires on it"
        touched = ", ".join(sorted(kinds - {ChangeKind.ANY}))
        triggers = ", ".join(sorted(self.binding.triggers))
        verb = "miss" if should_fire else "fire on"
        return f"{self.name}: {rule} triggers {triggers} {verb} the change, which touches {touched}"


@dataclass(frozen=True)
class TriggerTestRunner:
    root: Path
    ruleset: RulesetLoader
    ast_grep: AstGrep = AstGrep()

    def run(self) -> RuleTestResult:
        evals = rule_evals(self.ruleset.root)
        if not evals:
            return RuleTestResult()
        try:
            ruleset = self.ruleset.load()
        except ConfigError as error:
            return RuleTestResult(warnings=(f"trigger tests not run: {error}",))
        bindings = {binding.skill.name: binding for binding in Bindings.from_rulesets([ruleset])}
        named = [(file.relative_to(self.root), dataset) for file, dataset in evals]
        unknown = [
            f"{where}: no judge rule {dataset.name}"
            for where, dataset in named
            if dataset.name not in bindings
        ]
        checks = [
            _CaseCheck(
                bindings[dataset.name],
                case,
                name=f"{where} {case.name}",
                prefix=f"{dataset.name}/{number}/",
            )
            for where, dataset in named
            if dataset.name in bindings
            for number, case in enumerate(dataset.cases, start=1)
        ]
        changed = _classify_changes(checks, self.ast_grep, ruleset)
        failed = [problem for check in checks if (problem := check.problem(changed))]
        return RuleTestResult(problems=(*unknown, *failed))


def _classify_changes(
    checks: Sequence[_CaseCheck], ast_grep: AstGrep, ruleset: Ruleset
) -> ChangedLines:
    edits = {
        path: edit
        for check in checks
        for path, edit in check.case.inputs.edits(check.prefix).items()
    }
    with EditRepo.of(edits) as repo:
        return repo.classified(SyntaxScanner.for_rulesets(ast_grep, [ruleset]))
