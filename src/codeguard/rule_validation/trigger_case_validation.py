from dataclasses import dataclass
from pathlib import Path

from codeguard.ast_grep import AstGrep
from codeguard.config import (
    ChangeKind,
    ConfigError,
    Outcome,
    RuleEvalCase,
    RuleEvalReader,
    RulesetLoader,
)
from codeguard.repository import ChangedLines, LineScopes, WorkingTree
from codeguard.review import Binding, Bindings
from codeguard.rule_validation.validation_result import ValidationResult
from codeguard.syntax import ChangeClassifier, Classification, SyntaxScanner


@dataclass(frozen=True)
class _CaseCheck:
    binding: Binding
    case: RuleEvalCase
    name: str
    prefix: str

    @property
    def path(self) -> str:
        return f"{self.prefix}{self.case.inputs.file}"

    @property
    def before_files(self) -> dict[str, str]:
        return self.case.inputs.before_files(self.prefix)

    @property
    def after_files(self) -> dict[str, str]:
        return self.case.inputs.after_files(self.prefix)

    def problem(self, changed: ChangedLines, classification: Classification) -> str | None:
        rule = self.binding.judge_rule.name
        file = self.case.inputs.file
        expected = self.case.expected_output
        if not self.binding.files([file]):
            return f"{self.name}: {file} is outside the {rule} paths"
        if self.path not in changed.files:
            return f"{self.name}: the case changes no code in {file}"
        should_fire = expected.outcome is not Outcome.SKIPPED
        if classification.is_triggered(self.path, self.binding.triggers) == should_fire:
            return None
        kinds = classification.touched_kinds(self.path)
        if kinds is None:
            return f"{self.name}: {file} has no change kinds, so every {rule} trigger fires on it"
        touched = ", ".join(sorted(kinds - {ChangeKind.ANY}))
        triggers = ", ".join(sorted(self.binding.triggers))
        verb = "miss" if should_fire else "fire on"
        return f"{self.name}: {rule} triggers {triggers} {verb} the change, which touches {touched}"


@dataclass(frozen=True)
class TriggerCaseValidation:
    root: Path
    ruleset: RulesetLoader
    ast_grep: AstGrep = AstGrep()

    def run(self) -> ValidationResult:
        evals = RuleEvalReader(self.ruleset.root).read()
        if not evals:
            return ValidationResult()
        try:
            ruleset = self.ruleset.load()
        except ConfigError as error:
            return ValidationResult(warnings=(f"trigger tests not run: {error}",))
        bindings = {
            binding.judge_rule.name: binding for binding in Bindings.from_rulesets([ruleset])
        }
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
        before = {path: text for check in checks for path, text in check.before_files.items()}
        after = {path: text for check in checks for path, text in check.after_files.items()}
        with WorkingTree.temporary(before, after) as tree:
            changed = LineScopes.at(tree).changed_lines("HEAD")
            scanner = SyntaxScanner.for_rulesets(self.ast_grep, [ruleset])
            classification = ChangeClassifier(scanner, tree).classify(changed)
        failed = [
            problem for check in checks if (problem := check.problem(changed, classification))
        ]
        return ValidationResult(problems=(*unknown, *failed))
