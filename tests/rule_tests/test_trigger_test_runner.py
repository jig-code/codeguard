import textwrap

import pytest

from codeguard.config import ConfigError, RulesetLoader
from codeguard.rule_tests import RuleTestResult, TriggerTestRunner

EVAL_FILE = ".codeguard/rule-evals/enum-usage.yaml"


@pytest.fixture
def enum_rule(repo):
    repo.write(
        ".codeguard/skills/enum-usage/SKILL.md", "---\nname: enum-usage\n---\n# Enum usage\n"
    )
    repo.write(
        ".codeguard/bindings/enum-usage.yaml",
        'skill: .codeguard/skills/enum-usage\npaths: ["**/*.py"]\n'
        'exclude_paths: ["**/test_*.py"]\ntriggers: [enum-value, definition-added-or-removed]\n',
    )
    repo.write(
        ".codeguard/gates/enum-value.yml",
        "id: enum-value\nlanguage: python\nrule:\n  pattern: $X.value\n",
    )


def case(name: str, outcome: str, after: str, before: str | None = None, file: str | None = None):
    inputs = (f"      file: {file}\n" if file else "") + (
        f"      before: |\n{textwrap.indent(before, ' ' * 8)}" if before is not None else ""
    )
    return (
        f"  - name: {name}\n    inputs:\n{inputs}"
        f"      after: |\n{textwrap.indent(after, ' ' * 8)}"
        f"    expected_output:\n      outcome: {outcome}\n"
    )


def write_eval(repo, *cases: str) -> None:
    repo.write(EVAL_FILE, "cases:\n" + "".join(cases))


@pytest.mark.usefixtures("enum_rule")
class TestTriggerTestRunner:
    def test_invalid_case_whose_change_touches_a_gate_passes(self, repo):
        write_eval(
            repo,
            case(
                "reads the value",
                "invalid",
                "label = status.value\n",
                before="label = status.name\n",
            ),
        )

        result = TriggerTestRunner(repo.root, RulesetLoader.local(repo.root)).run()

        assert result == RuleTestResult()

    def test_invalid_case_whose_change_misses_the_triggers_fails_with_the_touched_kinds(self, repo):
        write_eval(
            repo,
            case(
                "changes a count",
                "invalid",
                "label = status.value\ncount = 2\n",
                before="label = status.value\ncount = 1\n",
            ),
        )

        result = TriggerTestRunner(repo.root, RulesetLoader.local(repo.root)).run()

        assert result == RuleTestResult(
            problems=(
                f"{EVAL_FILE} changes a count: enum-usage "
                "triggers definition-added-or-removed, gate:enum-value miss the change, which "
                "touches code, module-statement, number-literal",
            ),
        )

    def test_skipped_case_whose_change_touches_a_gate_fails(self, repo):
        write_eval(
            repo,
            case("reads the value", "skipped", "label = status.value\n"),
        )

        result = TriggerTestRunner(repo.root, RulesetLoader.local(repo.root)).run()

        assert result == RuleTestResult(
            problems=(
                f"{EVAL_FILE} reads the value: enum-usage "
                "triggers definition-added-or-removed, gate:enum-value fire on the change, which "
                "touches attribute-access, code, gate:enum-value, module-statement",
            ),
        )

    def test_skipped_case_whose_change_misses_the_triggers_passes(self, repo):
        write_eval(
            repo,
            case("changes a count", "skipped", "count = 2\n", before="count = 1\n"),
        )

        result = TriggerTestRunner(repo.root, RulesetLoader.local(repo.root)).run()

        assert result == RuleTestResult()

    def test_valid_case_whose_change_touches_a_gate_passes(self, repo):
        write_eval(repo, case("reads the value", "valid", "label = status.value\n"))

        result = TriggerTestRunner(repo.root, RulesetLoader.local(repo.root)).run()

        assert result == RuleTestResult()

    def test_valid_case_whose_change_misses_the_triggers_fails(self, repo):
        write_eval(repo, case("changes a count", "valid", "count = 2\n", before="count = 1\n"))

        result = TriggerTestRunner(repo.root, RulesetLoader.local(repo.root)).run()

        assert result == RuleTestResult(
            problems=(
                f"{EVAL_FILE} changes a count: enum-usage "
                "triggers definition-added-or-removed, gate:enum-value miss the change, which "
                "touches code, module-statement, number-literal",
            ),
        )

    def test_invalid_case_whose_removed_function_touches_definition_added_or_removed_passes(
        self, repo
    ):
        write_eval(
            repo,
            case(
                "removes a function",
                "invalid",
                "count = 1\n",
                before="def total():\n    return 1\n\n\ncount = 1\n",
            ),
        )

        result = TriggerTestRunner(repo.root, RulesetLoader.local(repo.root)).run()

        assert result == RuleTestResult()

    def test_case_file_outside_the_binding_paths_fails(self, repo):
        write_eval(
            repo,
            case("reads the value", "valid", "label = status.value\n", file="tests/test_status.py"),
        )

        result = TriggerTestRunner(repo.root, RulesetLoader.local(repo.root)).run()

        assert result == RuleTestResult(
            problems=(
                f"{EVAL_FILE} reads the value: "
                "tests/test_status.py is outside the enum-usage paths",
            ),
        )

    def test_case_without_a_change_fails(self, repo):
        write_eval(
            repo,
            case(
                "changes nothing",
                "invalid",
                "label = status.value\n",
                before="label = status.value\n",
            ),
        )

        result = TriggerTestRunner(repo.root, RulesetLoader.local(repo.root)).run()

        assert result == RuleTestResult(
            problems=(f"{EVAL_FILE} changes nothing: the case changes no code in module.py",),
        )

    def test_eval_for_an_unknown_rule_fails(self, repo):
        repo.write(".codeguard/rule-evals/enum-usag.yaml", "cases: []\n")

        result = TriggerTestRunner(repo.root, RulesetLoader.local(repo.root)).run()

        assert result == RuleTestResult(
            problems=(".codeguard/rule-evals/enum-usag.yaml: no judge rule enum-usag",)
        )


def test_ruleset_without_evals_passes(repo):
    result = TriggerTestRunner(repo.root, RulesetLoader.local(repo.root)).run()

    assert result == RuleTestResult()


@pytest.mark.usefixtures("enum_rule")
class TestInvalidEvalFiles:
    def test_case_without_expected_output_fails_the_run(self, repo):
        repo.write(EVAL_FILE, "cases:\n  - name: passes a string\n    inputs:\n      after: x\n")

        with pytest.raises(ConfigError) as error:
            TriggerTestRunner(repo.root, RulesetLoader.local(repo.root)).run()

        assert str(error.value) == (
            f"{repo.root / EVAL_FILE} is invalid:\n  cases.0.expected_output: Field required"
        )

    def test_case_whose_unchanged_files_list_its_own_file_fails_the_run(self, repo):
        repo.write(
            EVAL_FILE,
            "cases:\n"
            "  - name: reads the value\n"
            "    inputs:\n"
            "      after: label = status.value\n"
            "      unchanged:\n"
            "        module.py: label = status.name\n"
            "    expected_output: {outcome: valid}\n",
        )

        with pytest.raises(ConfigError) as error:
            TriggerTestRunner(repo.root, RulesetLoader.local(repo.root)).run()

        assert str(error.value) == (
            f"{repo.root / EVAL_FILE} is invalid:\n"
            "  cases.0.inputs: Value error, unchanged lists the edited file module.py"
        )

    @pytest.mark.parametrize("path", ["/etc/module.py", "../module.py", "./module.py", "."])
    def test_case_whose_unchanged_path_leaves_the_repository_or_is_not_normalized_fails_the_run(
        self, repo, path
    ):
        repo.write(
            EVAL_FILE,
            "cases:\n"
            "  - name: reads the value\n"
            "    inputs:\n"
            "      after: label = status.value\n"
            "      unchanged:\n"
            f"        {path}: label = status.name\n"
            "    expected_output: {outcome: valid}\n",
        )

        with pytest.raises(ConfigError) as error:
            TriggerTestRunner(repo.root, RulesetLoader.local(repo.root)).run()

        assert str(error.value) == (
            f"{repo.root / EVAL_FILE} is invalid:\n"
            f"  cases.0.inputs: Value error, {path} is not a normalized relative path"
        )

    def test_case_whose_file_leaves_the_repository_fails_the_run(self, repo):
        repo.write(
            EVAL_FILE,
            "cases:\n"
            "  - name: reads the value\n"
            "    inputs:\n"
            "      file: ../module.py\n"
            "      after: label = status.value\n"
            "    expected_output: {outcome: valid}\n",
        )

        with pytest.raises(ConfigError) as error:
            TriggerTestRunner(repo.root, RulesetLoader.local(repo.root)).run()

        assert str(error.value) == (
            f"{repo.root / EVAL_FILE} is invalid:\n"
            "  cases.0.inputs: Value error, ../module.py is not a normalized relative path"
        )

    def test_case_whose_unchanged_path_is_inside_git_fails_the_run(self, repo):
        repo.write(
            EVAL_FILE,
            "cases:\n"
            "  - name: reads the value\n"
            "    inputs:\n"
            "      after: label = status.value\n"
            "      unchanged:\n"
            "        .git/config: '[core]'\n"
            "    expected_output: {outcome: valid}\n",
        )

        with pytest.raises(ConfigError) as error:
            TriggerTestRunner(repo.root, RulesetLoader.local(repo.root)).run()

        assert str(error.value) == (
            f"{repo.root / EVAL_FILE} is invalid:\n"
            "  cases.0.inputs: Value error, .git/config is inside .git"
        )
