from importlib.metadata import version

import pytest
import yaml
from recording_judge import FailingJudge, RecordingJudge, RecordingJudges

from codeguard.config import JudgeModel, JudgeProvider, RulesetLoader
from codeguard.judge_evals import EvalSelection, JudgeEvalResult, JudgeEvalRunner
from codeguard.review import Bindings
from codeguard.rule_tests import RuleTestResult


@pytest.fixture
def enum_rule(repo):
    repo.write(
        ".codeguard/skills/enum-usage/SKILL.md",
        "---\nname: enum-usage\n---\n# Enum usage\n\nPass the enum member, never a bare literal.\n",
    )
    repo.write(
        ".codeguard/bindings/enum-usage.yaml",
        yaml.safe_dump(
            {
                "skill": ".codeguard/skills/enum-usage",
                "paths": ["**/*.py"],
                "triggers": ["any"],
                "model": "claude-haiku-5-5",
            }
        ),
    )


def a_case(name: str, after: str, outcome: str = "valid") -> dict[str, object]:
    return {"name": name, "inputs": {"after": after}, "expected_output": {"outcome": outcome}}


@pytest.mark.usefixtures("enum_rule")
class TestJudgeEvalRunner:
    def test_rule_is_reported_as_one_experiment_named_after_the_rule_and_model(self, repo):
        repo.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump({"cases": [a_case("a string", "ship(status='shipped')\n")]}),
        )
        runner = JudgeEvalRunner(
            repo.root, RulesetLoader.local(repo.root), RecordingJudges(RecordingJudge()), 0.9
        )

        result = runner.run()

        assert [report.name for report in result.reports] == ["enum-usage on claude-haiku-5-5"]
        assert [report.dataset_name for report in result.reports] == ["enum-usage"]

    def test_experiment_records_the_model_and_the_rule_and_codeguard_versions(self, repo):
        repo.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump({"cases": [a_case("a string", "ship(status='shipped')\n")]}),
        )
        loader = RulesetLoader.local(repo.root)
        [binding] = Bindings.from_rulesets([loader.load()])
        runner = JudgeEvalRunner(repo.root, loader, RecordingJudges(RecordingJudge()), 0.9)

        result = runner.run()

        assert result.reports[0].experiment_metadata == {
            "provider": "claude-cli",
            "model": "claude-haiku-5-5",
            "confidence_threshold": 0.9,
            "rule_version": binding.version_for("python"),
            "codeguard_version": version("codeguard"),
        }

    def test_case_is_judged_with_the_model_the_binding_names(self, repo):
        repo.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump({"cases": [a_case("a string", "ship(status='shipped')\n")]}),
        )
        judges = RecordingJudges(RecordingJudge())
        runner = JudgeEvalRunner(repo.root, RulesetLoader.local(repo.root), judges, 0.9)

        runner.run()

        assert [creation.model for creation in judges.created] == [
            JudgeModel(provider=JudgeProvider.CLAUDE_CLI, name="claude-haiku-5-5")
        ]

    def test_given_model_judges_instead_of_the_binding_s(self, repo):
        repo.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump({"cases": [a_case("a string", "ship(status='shipped')\n")]}),
        )
        judges = RecordingJudges(RecordingJudge())
        gemini = JudgeModel(provider=JudgeProvider.GEMINI, name="gemini-3.1-pro-preview")
        runner = JudgeEvalRunner(
            repo.root, RulesetLoader.local(repo.root), judges, 0.9, model=gemini
        )

        result = runner.run()

        assert [creation.model for creation in judges.created] == [gemini]
        assert [report.name for report in result.reports] == [
            "enum-usage on gemini-3.1-pro-preview"
        ]

    def test_failing_case_fails_once_per_repeat_numbered(self, repo, make_verdict, make_violation):
        repo.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump({"cases": [a_case("a string", "ship(status='shipped')\n")]}),
        )
        verdict = make_verdict(
            breaking=True, violations=(make_violation(file="module.py", message="Rename it."),)
        )
        runner = JudgeEvalRunner(
            repo.root,
            RulesetLoader.local(repo.root),
            RecordingJudges(RecordingJudge(verdict)),
            0.9,
            repeat=2,
        )

        result = runner.run()

        assert sorted(result.failures) == [
            f"enum-usage a string [{run}/2]: expected outcome valid, got outcome invalid\n"
            "  reason: The code breaks the convention.\n  line 1 (1.00): Rename it."
            for run in (1, 2)
        ]

    def test_judge_error_is_reported_as_a_case_not_judged(self, repo):
        repo.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump({"cases": [a_case("a string", "ship(status='shipped')\n")]}),
        )
        runner = JudgeEvalRunner(
            repo.root, RulesetLoader.local(repo.root), RecordingJudges(FailingJudge()), 0.9
        )

        result = runner.run()

        assert result.failures == (
            "enum-usage a string: not judged: "
            "JudgeError: gemini failed with 502: upstream request failed",
        )

    def test_eval_for_an_unknown_rule_is_reported_as_a_problem(self, repo):
        repo.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump(
                {"name": "enum-usge", "cases": [a_case("a string", "ship(status='shipped')\n")]}
            ),
        )
        runner = JudgeEvalRunner(
            repo.root, RulesetLoader.local(repo.root), RecordingJudges(RecordingJudge()), 0.9
        )

        result = runner.run()

        assert result == JudgeEvalResult(
            checks=RuleTestResult(
                problems=(".codeguard/rule-evals/enum-usage.yaml: no judge rule enum-usge",)
            )
        )

    def test_selected_case_name_judges_only_the_cases_holding_it(self, repo):
        repo.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump(
                {
                    "cases": [
                        a_case("a string", "ship(status='shipped')\n", "invalid"),
                        a_case("the member", "ship(status=Status.SHIPPED)\n"),
                    ]
                }
            ),
        )
        runner = JudgeEvalRunner(
            repo.root,
            RulesetLoader.local(repo.root),
            RecordingJudges(RecordingJudge()),
            0.9,
            selection=EvalSelection(cases=("member",)),
        )

        result = runner.run()

        assert [case.name for report in result.reports for case in report.cases] == ["the member"]

    def test_rule_not_selected_is_neither_judged_nor_reported(self, repo):
        repo.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump({"cases": [a_case("a string", "ship(status='shipped')\n")]}),
        )
        judges = RecordingJudges(RecordingJudge())
        runner = JudgeEvalRunner(
            repo.root,
            RulesetLoader.local(repo.root),
            judges,
            0.9,
            selection=EvalSelection(rules=frozenset({"other-rule"})),
        )

        result = runner.run()

        assert result == JudgeEvalResult()
        assert judges.created == []

    def test_case_names_lists_each_judge_rule_s_cases(self, repo):
        repo.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump(
                {
                    "cases": [
                        a_case("a string", "ship(status='shipped')\n", "invalid"),
                        a_case("the member", "ship(status=Status.SHIPPED)\n"),
                    ]
                }
            ),
        )
        runner = JudgeEvalRunner(
            repo.root, RulesetLoader.local(repo.root), RecordingJudges(RecordingJudge()), 0.9
        )

        names = runner.case_names()

        assert names == {"enum-usage": ("a string", "the member")}

    def test_judge_reason_is_reported_for_each_judged_case(self, repo, make_verdict):
        repo.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump({"cases": [a_case("a string", "ship(status='shipped')\n")]}),
        )
        verdict = make_verdict(reason="The call passes a string.")
        runner = JudgeEvalRunner(
            repo.root, RulesetLoader.local(repo.root), RecordingJudges(RecordingJudge(verdict)), 0.9
        )

        result = runner.run()

        assert result.reasons == ("enum-usage a string: The call passes a string.",)

    def test_eval_without_cases_fails_as_no_case_evaluated(self, repo):
        repo.write(".codeguard/rule-evals/enum-usage.yaml", yaml.safe_dump({"cases": []}))
        runner = JudgeEvalRunner(
            repo.root, RulesetLoader.local(repo.root), RecordingJudges(RecordingJudge()), 0.9
        )

        result = runner.run()

        assert result.failures == ("enum-usage: no case was evaluated",)

    def test_rule_with_no_case_selected_is_left_out(self, repo):
        repo.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump({"cases": [a_case("a string", "ship(status='shipped')\n")]}),
        )
        runner = JudgeEvalRunner(
            repo.root,
            RulesetLoader.local(repo.root),
            RecordingJudges(RecordingJudge()),
            0.9,
            selection=EvalSelection(cases=("member",)),
        )

        result = runner.run()

        assert result == JudgeEvalResult()
