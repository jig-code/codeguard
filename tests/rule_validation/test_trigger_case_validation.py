import yaml

from codeguard.config import RulesetLoader
from codeguard.rule_validation import TriggerCaseValidation, ValidationResult

EVAL_FILE = ".codeguard/rule-evals/enum-usage.yaml"


ENUM_RULE = "# Enum usage\n"
ENUM_BINDING = {
    "rule": "enum-usage",
    "paths": ["**/*.py"],
    "exclude_paths": ["**/test_*.py"],
    "triggers": ["enum-value", "definition-added-or-removed"],
}
ENUM_GATE = {"id": "enum-value", "language": "python", "rule": {"pattern": "$X.value"}}


def case(name: str, outcome: str, after: str, before: str | None = None, file: str | None = None):
    inputs = (
        ({"file": file} if file else {})
        | ({"before": before} if before is not None else {})
        | {"after": after}
    )
    return {"name": name, "inputs": inputs, "expected_output": {"outcome": outcome}}


def write_eval(directory, *cases: dict) -> None:
    directory.write(EVAL_FILE, yaml.safe_dump({"cases": list(cases)}))


class TestTriggerCaseValidation:
    def test_invalid_case_whose_change_touches_a_gate_passes(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", yaml.safe_dump(ENUM_BINDING))
        directory.write(".codeguard/gates/enum-value.yml", yaml.safe_dump(ENUM_GATE))
        write_eval(
            directory,
            case(
                "reading the value",
                "invalid",
                "label = status.value\n",
                before="label = status.name\n",
            ),
        )

        result = TriggerCaseValidation(directory.root, RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult()

    def test_invalid_case_whose_change_misses_the_triggers_fails_with_the_touched_kinds(
        self, directory
    ):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", yaml.safe_dump(ENUM_BINDING))
        directory.write(".codeguard/gates/enum-value.yml", yaml.safe_dump(ENUM_GATE))
        write_eval(
            directory,
            case(
                "a count change",
                "invalid",
                "label = status.value\ncount = 2\n",
                before="label = status.value\ncount = 1\n",
            ),
        )

        result = TriggerCaseValidation(directory.root, RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult(
            problems=(
                f"{EVAL_FILE} a count change: enum-usage "
                "triggers definition-added-or-removed, gate:enum-value miss the change, which "
                "touches code, module-statement, number-literal",
            ),
        )

    def test_skipped_case_whose_change_touches_a_gate_fails(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", yaml.safe_dump(ENUM_BINDING))
        directory.write(".codeguard/gates/enum-value.yml", yaml.safe_dump(ENUM_GATE))
        write_eval(
            directory,
            case("reading the value", "skipped", "label = status.value\n"),
        )

        result = TriggerCaseValidation(directory.root, RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult(
            problems=(
                f"{EVAL_FILE} reading the value: enum-usage "
                "triggers definition-added-or-removed, gate:enum-value fire on the change, which "
                "touches attribute-access, code, gate:enum-value, module-statement",
            ),
        )

    def test_skipped_case_whose_change_misses_the_triggers_passes(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", yaml.safe_dump(ENUM_BINDING))
        directory.write(".codeguard/gates/enum-value.yml", yaml.safe_dump(ENUM_GATE))
        write_eval(
            directory,
            case("a count change", "skipped", "count = 2\n", before="count = 1\n"),
        )

        result = TriggerCaseValidation(directory.root, RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult()

    def test_valid_case_whose_change_touches_a_gate_passes(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", yaml.safe_dump(ENUM_BINDING))
        directory.write(".codeguard/gates/enum-value.yml", yaml.safe_dump(ENUM_GATE))
        write_eval(directory, case("reading the value", "valid", "label = status.value\n"))

        result = TriggerCaseValidation(directory.root, RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult()

    def test_valid_case_whose_change_misses_the_triggers_fails(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", yaml.safe_dump(ENUM_BINDING))
        directory.write(".codeguard/gates/enum-value.yml", yaml.safe_dump(ENUM_GATE))
        write_eval(directory, case("a count change", "valid", "count = 2\n", before="count = 1\n"))

        result = TriggerCaseValidation(directory.root, RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult(
            problems=(
                f"{EVAL_FILE} a count change: enum-usage "
                "triggers definition-added-or-removed, gate:enum-value miss the change, which "
                "touches code, module-statement, number-literal",
            ),
        )

    def test_invalid_case_whose_removed_function_touches_definition_added_or_removed_passes(
        self, directory
    ):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", yaml.safe_dump(ENUM_BINDING))
        directory.write(".codeguard/gates/enum-value.yml", yaml.safe_dump(ENUM_GATE))
        write_eval(
            directory,
            case(
                "removes a function",
                "invalid",
                "count = 1\n",
                before="def total():\n    return 1\n\n\ncount = 1\n",
            ),
        )

        result = TriggerCaseValidation(directory.root, RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult()

    def test_case_file_outside_the_binding_paths_fails(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", yaml.safe_dump(ENUM_BINDING))
        directory.write(".codeguard/gates/enum-value.yml", yaml.safe_dump(ENUM_GATE))
        write_eval(
            directory,
            case(
                "reading the value",
                "valid",
                "label = status.value\n",
                file="tests/test_status.py",
            ),
        )

        result = TriggerCaseValidation(directory.root, RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult(
            problems=(
                f"{EVAL_FILE} reading the value: "
                "tests/test_status.py is outside the enum-usage paths",
            ),
        )

    def test_case_without_a_change_fails(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", yaml.safe_dump(ENUM_BINDING))
        directory.write(".codeguard/gates/enum-value.yml", yaml.safe_dump(ENUM_GATE))
        write_eval(
            directory,
            case(
                "changes nothing",
                "invalid",
                "label = status.value\n",
                before="label = status.value\n",
            ),
        )

        result = TriggerCaseValidation(directory.root, RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult(
            problems=(f"{EVAL_FILE} changes nothing: the case changes no code in module.py",),
        )

    def test_eval_for_an_unknown_rule_fails(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", yaml.safe_dump(ENUM_BINDING))
        directory.write(".codeguard/gates/enum-value.yml", yaml.safe_dump(ENUM_GATE))
        directory.write(".codeguard/rule-evals/enum-usag.yaml", yaml.safe_dump({"cases": []}))

        result = TriggerCaseValidation(directory.root, RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult(
            problems=(".codeguard/rule-evals/enum-usag.yaml: no judge rule enum-usag",)
        )


def test_ruleset_without_evals_passes(directory):
    directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
    directory.write(".codeguard/bindings/enum-usage.yaml", yaml.safe_dump(ENUM_BINDING))
    directory.write(".codeguard/gates/enum-value.yml", yaml.safe_dump(ENUM_GATE))
    result = TriggerCaseValidation(directory.root, RulesetLoader.local(directory.root)).run()

    assert result == ValidationResult()
