import pytest
import yaml
from claude_output import claude_stream
from fake_cli import configure_fake_cli_response
from rules_package import write_package

from codeguard.config import ConfigError
from codeguard.judge_evals import EvalSelection, JudgeEvalResult
from codeguard.repository import WorkingTree
from codeguard.rule_validation import ValidationResult
from codeguard.rules import Rules
from codeguard.rules.rule_evaluation import RuleEvaluation


@pytest.fixture
def placement_case() -> dict[str, object]:
    return {
        "name": "an assignment in the invoice",
        "inputs": {"file": "invoice.py", "after": "x = 1\n"},
        "expected_output": {"outcome": "invalid"},
    }


@pytest.fixture
def gemini_binding() -> dict[str, object]:
    return {
        "paths": ["**/*.py"],
        "triggers": ["any"],
        "provider": "gemini",
        "model": "gemini-judge-test",
    }


@pytest.mark.usefixtures("fake_cli_config", "judgement_cache")
class TestRuleEvaluation:
    @pytest.mark.usefixtures("fake_claude_on_path")
    def test_each_run_calls_the_model_again(self, git_repo, placement_case, tmp_path):
        write_package(git_repo)
        git_repo.write(
            "python/rule-evals/responsibility-placement.yaml",
            yaml.safe_dump({"cases": [placement_case]}),
        )
        calls = tmp_path / "calls"
        configure_fake_cli_response({"stdout": claude_stream([]), "calls": str(calls)})
        evaluation = RuleEvaluation(Rules(WorkingTree.at(git_repo.root)))

        evaluation.run()
        evaluation.run()

        assert calls.read_text() == "called\ncalled\n"

    @pytest.mark.usefixtures("fake_claude_on_path")
    def test_selection_problem_is_reported_without_calling_the_model(
        self, git_repo, placement_case, tmp_path
    ):
        write_package(git_repo)
        git_repo.write(
            "python/rule-evals/responsibility-placement.yaml",
            yaml.safe_dump({"cases": [placement_case]}),
        )
        calls = tmp_path / "calls"
        configure_fake_cli_response({"stdout": claude_stream([]), "calls": str(calls)})
        evaluation = RuleEvaluation(Rules(WorkingTree.at(git_repo.root)))

        result = evaluation.run(selection=EvalSelection(cases=("refunds",)))

        assert result == JudgeEvalResult(
            checks=ValidationResult(
                problems=("--case refunds: no case of the selected rules has it in its name",)
            )
        )
        assert not calls.exists()

    def test_gemini_rule_without_a_gemini_sign_in_is_an_error(
        self, git_repo, placement_case, gemini_binding
    ):
        write_package(git_repo)
        git_repo.write(
            "python/bindings/responsibility-placement.yaml",
            yaml.safe_dump({"rule": "responsibility-placement", **gemini_binding}),
        )
        git_repo.write(
            "python/rule-evals/responsibility-placement.yaml",
            yaml.safe_dump({"cases": [placement_case]}),
        )
        evaluation = RuleEvaluation(Rules(WorkingTree.at(git_repo.root)))

        with pytest.raises(ConfigError) as error:
            evaluation.run()

        assert str(error.value) == "Gemini needs a project: set CODEGUARD_JUDGE__GEMINI__PROJECT"

    @pytest.mark.usefixtures("fake_claude_on_path")
    def test_gemini_rule_the_selection_leaves_out_needs_no_gemini_sign_in(  # noqa: PLR0913 - pytest fixtures
        self, git_repo, placement_case, gemini_binding, make_judge_rule, tmp_path
    ):
        write_package(git_repo)
        git_repo.write(
            "python/rule-evals/responsibility-placement.yaml",
            yaml.safe_dump({"cases": [placement_case]}),
        )
        git_repo.write("python/rules/judge/naming.md", make_judge_rule().text)
        git_repo.write(
            "python/bindings/naming.yaml", yaml.safe_dump({"rule": "naming", **gemini_binding})
        )
        git_repo.write(
            "python/rule-evals/naming.yaml",
            yaml.safe_dump({"cases": [{**placement_case, "name": "names the helper"}]}),
        )
        calls = tmp_path / "calls"
        configure_fake_cli_response({"stdout": claude_stream([]), "calls": str(calls)})
        evaluation = RuleEvaluation(Rules(WorkingTree.at(git_repo.root)))

        evaluation.run(selection=EvalSelection(rules=frozenset({"responsibility-placement"})))

        assert calls.read_text() == "called\n"
