import textwrap

from codeguard.config import RulesetLoader
from codeguard.rule_tests import RuleTestResult, TriggerTestRunner

EVAL_FILE = ".codeguard/rule-evals/enum-usage.yaml"


ENUM_RULE = "# Enum usage\n"
ENUM_BINDING = (
    'rule: enum-usage\npaths: ["**/*.py"]\n'
    'exclude_paths: ["**/test_*.py"]\ntriggers: [enum-value, definition-added-or-removed]\n'
)
ENUM_GATE = "id: enum-value\nlanguage: python\nrule:\n  pattern: $X.value\n"


def case(name: str, outcome: str, after: str, before: str | None = None, file: str | None = None):
    inputs = (f"      file: {file}\n" if file else "") + (
        f"      before: |\n{textwrap.indent(before, ' ' * 8)}" if before is not None else ""
    )
    return (
        f"  - name: {name}\n    inputs:\n{inputs}"
        f"      after: |\n{textwrap.indent(after, ' ' * 8)}"
        f"    expected_output:\n      outcome: {outcome}\n"
    )


def write_eval(directory, *cases: str) -> None:
    directory.write(EVAL_FILE, "cases:\n" + "".join(cases))


class TestTriggerTestRunner:
    def test_invalid_case_whose_change_touches_a_gate_passes(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(".codeguard/gates/enum-value.yml", ENUM_GATE)
        write_eval(
            directory,
            case(
                "reading the value",
                "invalid",
                "label = status.value\n",
                before="label = status.name\n",
            ),
        )

        result = TriggerTestRunner(directory.root, RulesetLoader.local(directory.root)).run()

        assert result == RuleTestResult()

    def test_invalid_case_whose_change_misses_the_triggers_fails_with_the_touched_kinds(
        self, directory
    ):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(".codeguard/gates/enum-value.yml", ENUM_GATE)
        write_eval(
            directory,
            case(
                "a count change",
                "invalid",
                "label = status.value\ncount = 2\n",
                before="label = status.value\ncount = 1\n",
            ),
        )

        result = TriggerTestRunner(directory.root, RulesetLoader.local(directory.root)).run()

        assert result == RuleTestResult(
            problems=(
                f"{EVAL_FILE} a count change: enum-usage "
                "triggers definition-added-or-removed, gate:enum-value miss the change, which "
                "touches code, module-statement, number-literal",
            ),
        )

    def test_skipped_case_whose_change_touches_a_gate_fails(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(".codeguard/gates/enum-value.yml", ENUM_GATE)
        write_eval(
            directory,
            case("reading the value", "skipped", "label = status.value\n"),
        )

        result = TriggerTestRunner(directory.root, RulesetLoader.local(directory.root)).run()

        assert result == RuleTestResult(
            problems=(
                f"{EVAL_FILE} reading the value: enum-usage "
                "triggers definition-added-or-removed, gate:enum-value fire on the change, which "
                "touches attribute-access, code, gate:enum-value, module-statement",
            ),
        )

    def test_skipped_case_whose_change_misses_the_triggers_passes(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(".codeguard/gates/enum-value.yml", ENUM_GATE)
        write_eval(
            directory,
            case("a count change", "skipped", "count = 2\n", before="count = 1\n"),
        )

        result = TriggerTestRunner(directory.root, RulesetLoader.local(directory.root)).run()

        assert result == RuleTestResult()

    def test_valid_case_whose_change_touches_a_gate_passes(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(".codeguard/gates/enum-value.yml", ENUM_GATE)
        write_eval(directory, case("reading the value", "valid", "label = status.value\n"))

        result = TriggerTestRunner(directory.root, RulesetLoader.local(directory.root)).run()

        assert result == RuleTestResult()

    def test_valid_case_whose_change_misses_the_triggers_fails(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(".codeguard/gates/enum-value.yml", ENUM_GATE)
        write_eval(directory, case("a count change", "valid", "count = 2\n", before="count = 1\n"))

        result = TriggerTestRunner(directory.root, RulesetLoader.local(directory.root)).run()

        assert result == RuleTestResult(
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
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(".codeguard/gates/enum-value.yml", ENUM_GATE)
        write_eval(
            directory,
            case(
                "removes a function",
                "invalid",
                "count = 1\n",
                before="def total():\n    return 1\n\n\ncount = 1\n",
            ),
        )

        result = TriggerTestRunner(directory.root, RulesetLoader.local(directory.root)).run()

        assert result == RuleTestResult()

    def test_case_file_outside_the_binding_paths_fails(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(".codeguard/gates/enum-value.yml", ENUM_GATE)
        write_eval(
            directory,
            case(
                "reading the value",
                "valid",
                "label = status.value\n",
                file="tests/test_status.py",
            ),
        )

        result = TriggerTestRunner(directory.root, RulesetLoader.local(directory.root)).run()

        assert result == RuleTestResult(
            problems=(
                f"{EVAL_FILE} reading the value: "
                "tests/test_status.py is outside the enum-usage paths",
            ),
        )

    def test_case_without_a_change_fails(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(".codeguard/gates/enum-value.yml", ENUM_GATE)
        write_eval(
            directory,
            case(
                "changes nothing",
                "invalid",
                "label = status.value\n",
                before="label = status.value\n",
            ),
        )

        result = TriggerTestRunner(directory.root, RulesetLoader.local(directory.root)).run()

        assert result == RuleTestResult(
            problems=(f"{EVAL_FILE} changes nothing: the case changes no code in module.py",),
        )

    def test_eval_for_an_unknown_rule_fails(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(".codeguard/gates/enum-value.yml", ENUM_GATE)
        directory.write(".codeguard/rule-evals/enum-usag.yaml", "cases: []\n")

        result = TriggerTestRunner(directory.root, RulesetLoader.local(directory.root)).run()

        assert result == RuleTestResult(
            problems=(".codeguard/rule-evals/enum-usag.yaml: no judge rule enum-usag",)
        )


def test_ruleset_without_evals_passes(directory):
    directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
    directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
    directory.write(".codeguard/gates/enum-value.yml", ENUM_GATE)
    result = TriggerTestRunner(directory.root, RulesetLoader.local(directory.root)).run()

    assert result == RuleTestResult()
