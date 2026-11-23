import pytest
import yaml
from recording_judge import RecordingJudge, RecordingJudges
from rules_package import write_package

from codeguard.ast_grep import AstGrep
from codeguard.config import Config, ConfigError, GeminiSettings, RulesetLoader
from codeguard.judge_evals import EvalSelection, JudgeEvalResult
from codeguard.project import Project
from codeguard.project.rule_evaluation import RuleEvaluation
from codeguard.repository import WorkingTree
from codeguard.rule_validation import ValidationResult


@pytest.fixture
def package(directory):
    write_package(directory)
    return directory


@pytest.fixture
def project(package) -> Project:
    return Project(WorkingTree.at(package.root), Config(), AstGrep())


@pytest.fixture
def python_ruleset(package) -> RulesetLoader:
    return RulesetLoader(repo=package.root, root=package.root / "python", name="example/python")


@pytest.fixture
def gemini_binding() -> dict[str, object]:
    return {
        "paths": ["**/*.py"],
        "triggers": ["any"],
        "provider": "gemini",
        "model": "gemini-judge-test",
    }


class TestRuleEvaluation:
    def test_selection_problem_is_reported_without_making_a_judge(
        self, package, project, python_ruleset
    ):
        package.write(
            "python/rule-evals/responsibility-placement.yaml",
            yaml.safe_dump(
                {
                    "cases": [
                        {
                            "name": "an assignment in the invoice",
                            "inputs": {"file": "invoice.py", "after": "x = 1\n"},
                            "expected_output": {"outcome": "invalid"},
                        }
                    ]
                }
            ),
        )
        judges = RecordingJudges(RecordingJudge())
        evaluation = RuleEvaluation(project, [python_ruleset], judges, GeminiSettings())

        result = evaluation.run(selection=EvalSelection(cases=("refunds",)))

        assert result == JudgeEvalResult(
            checks=ValidationResult(
                problems=("--case refunds: no case of the selected rules has it in its name",)
            )
        )
        assert judges.created == []

    def test_gemini_rule_without_a_gemini_sign_in_is_an_error(
        self, package, project, python_ruleset, gemini_binding
    ):
        package.write(
            "python/bindings/responsibility-placement.yaml",
            yaml.safe_dump({"rule": "responsibility-placement", **gemini_binding}),
        )
        package.write(
            "python/rule-evals/responsibility-placement.yaml",
            yaml.safe_dump(
                {
                    "cases": [
                        {
                            "name": "an assignment in the invoice",
                            "inputs": {"file": "invoice.py", "after": "x = 1\n"},
                            "expected_output": {"outcome": "invalid"},
                        }
                    ]
                }
            ),
        )
        evaluation = RuleEvaluation(
            project, [python_ruleset], RecordingJudges(RecordingJudge()), GeminiSettings()
        )

        with pytest.raises(ConfigError) as error:
            evaluation.run()

        assert str(error.value) == "Gemini needs a project: set CODEGUARD_JUDGE__GEMINI__PROJECT"

    def test_gemini_rule_the_selection_leaves_out_needs_no_gemini_sign_in(  # noqa: PLR0913 - pytest fixtures
        self, package, project, python_ruleset, gemini_binding, make_judge_rule
    ):
        package.write(
            "python/rule-evals/responsibility-placement.yaml",
            yaml.safe_dump(
                {
                    "cases": [
                        {
                            "name": "a Ruby file the binding leaves out",
                            "inputs": {"file": "invoice.rb", "after": "x = 1\n"},
                            "expected_output": {"outcome": "skipped"},
                        }
                    ]
                }
            ),
        )
        package.write("python/rules/judge/naming.md", make_judge_rule().text)
        package.write(
            "python/bindings/naming.yaml", yaml.safe_dump({"rule": "naming", **gemini_binding})
        )
        package.write(
            "python/rule-evals/naming.yaml",
            yaml.safe_dump(
                {
                    "cases": [
                        {
                            "name": "names the helper",
                            "inputs": {"file": "invoice.py", "after": "x = 1\n"},
                            "expected_output": {"outcome": "invalid"},
                        }
                    ]
                }
            ),
        )
        evaluation = RuleEvaluation(
            project, [python_ruleset], RecordingJudges(RecordingJudge()), GeminiSettings()
        )

        result = evaluation.run(
            selection=EvalSelection(rules=frozenset({"responsibility-placement"}))
        )

        assert [report.name for report in result.reports] == [
            "responsibility-placement on claude-cli's default model"
        ]
