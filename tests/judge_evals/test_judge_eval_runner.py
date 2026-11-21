from importlib.metadata import version

import yaml
from recording_judge import FailingJudge, RecordingJudge, RecordingJudges, SequencedJudge

from codeguard.config import JudgeChoice, JudgeConfig, JudgeModel, JudgeProvider, RulesetLoader
from codeguard.judge_evals import EvalSelection, JudgeEvalResult, JudgeEvalRunner
from codeguard.review import Bindings
from codeguard.rule_validation import ValidationResult

ENUM_RULE = "# Enum usage\n\nPass the enum member, never a bare literal.\n"
ENUM_BINDING = yaml.safe_dump(
    {"rule": "enum-usage", "paths": ["**/*.py"], "triggers": ["any"], "model": "claude-haiku-5-5"}
)


class TestJudgeEvalRunner:
    def test_rule_is_reported_as_one_experiment_named_after_the_rule_and_model(
        self, directory, make_rule_eval_case
    ):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump(
                {"cases": [make_rule_eval_case().model_dump(mode="json", exclude_defaults=True)]}
            ),
        )
        runner = JudgeEvalRunner(
            directory.root,
            RulesetLoader.local(directory.root),
            RecordingJudges(RecordingJudge()),
        )

        result = runner.run()

        assert [report.name for report in result.reports] == ["enum-usage on claude-haiku-5-5"]
        assert [report.dataset_name for report in result.reports] == ["enum-usage"]

    def test_experiment_records_the_model_and_the_rule_and_codeguard_versions(
        self, directory, make_rule_eval_case
    ):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump(
                {"cases": [make_rule_eval_case().model_dump(mode="json", exclude_defaults=True)]}
            ),
        )
        loader = RulesetLoader.local(directory.root)
        [binding] = Bindings.from_rulesets([loader.load()])
        runner = JudgeEvalRunner(directory.root, loader, RecordingJudges(RecordingJudge()))

        result = runner.run()

        assert result.reports[0].experiment_metadata == {
            "provider": "claude-cli",
            "model": "claude-haiku-5-5",
            "rule_version": binding.version,
            "codeguard_version": version("codeguard"),
        }

    def test_case_is_judged_with_the_model_the_binding_names(self, directory, make_rule_eval_case):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump(
                {"cases": [make_rule_eval_case().model_dump(mode="json", exclude_defaults=True)]}
            ),
        )
        judges = RecordingJudges(RecordingJudge())
        runner = JudgeEvalRunner(directory.root, RulesetLoader.local(directory.root), judges)

        runner.run()

        assert [creation.model for creation in judges.created] == [
            JudgeModel(provider=JudgeProvider.CLAUDE_CLI, name="claude-haiku-5-5")
        ]

    def test_given_model_judges_instead_of_the_binding_s(self, directory, make_rule_eval_case):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump(
                {"cases": [make_rule_eval_case().model_dump(mode="json", exclude_defaults=True)]}
            ),
        )
        judges = RecordingJudges(RecordingJudge())
        model = "gemini-judge-test"
        gemini = JudgeChoice(provider=JudgeProvider.GEMINI, model=model)
        runner = JudgeEvalRunner(
            directory.root, RulesetLoader.local(directory.root), judges, judge_override=gemini
        )

        result = runner.run()

        assert [creation.model for creation in judges.created] == [
            JudgeModel(provider=JudgeProvider.GEMINI, name=model)
        ]
        assert [report.name for report in result.reports] == [f"enum-usage on {model}"]

    def test_failing_case_fails_once_per_repeat_numbered(
        self, directory, make_rule_eval_case, make_verdict, make_violation
    ):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump(
                {"cases": [make_rule_eval_case().model_dump(mode="json", exclude_defaults=True)]}
            ),
        )
        verdict = make_verdict(
            breaking=True, violations=(make_violation(file="module.py", message="Rename it."),)
        )
        runner = JudgeEvalRunner(
            directory.root,
            RulesetLoader.local(directory.root),
            RecordingJudges(RecordingJudge(verdict)),
            repeat=2,
        )

        result = runner.run()

        assert sorted(result.failures) == [
            f"enum-usage a string [{run}/2]: expected outcome valid, got outcome invalid\n"
            "  reason: The code breaks the convention.\n  line 1: Rename it."
            for run in (1, 2)
        ]

    def test_case_passes_when_every_run_gives_its_expected_outcome(
        self, directory, make_rule_eval_case
    ):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump(
                {"cases": [make_rule_eval_case().model_dump(mode="json", exclude_defaults=True)]}
            ),
        )
        runner = JudgeEvalRunner(
            directory.root,
            RulesetLoader.local(directory.root),
            RecordingJudges(RecordingJudge()),
            repeat=3,
        )

        result = runner.run()

        assert result.passed
        assert result.failures == ()

    def test_case_fails_when_any_run_gives_another_outcome(
        self, directory, make_rule_eval_case, make_verdict, make_violation
    ):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump(
                {"cases": [make_rule_eval_case().model_dump(mode="json", exclude_defaults=True)]}
            ),
        )
        breaking = make_verdict(
            breaking=True, violations=(make_violation(file="module.py", message="Rename it."),)
        )
        judge = SequencedJudge([make_verdict(), breaking, make_verdict()])
        one_call_at_once = JudgeConfig(calls_at_once=1)
        gemini = JudgeChoice(provider=JudgeProvider.GEMINI, model="gemini-judge-test")
        runner = JudgeEvalRunner(
            directory.root,
            RulesetLoader.local(directory.root),
            RecordingJudges(judge),
            repeat=3,
            judge_config=one_call_at_once,
            judge_override=gemini,
        )

        result = runner.run()

        assert not result.passed
        assert result.failures == (
            "enum-usage a string [2/3]: expected outcome valid, got outcome invalid\n"
            "  reason: The code breaks the convention.\n  line 1: Rename it.",
        )

    def test_judge_error_is_reported_as_a_case_not_judged(self, directory, make_rule_eval_case):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump(
                {"cases": [make_rule_eval_case().model_dump(mode="json", exclude_defaults=True)]}
            ),
        )
        runner = JudgeEvalRunner(
            directory.root,
            RulesetLoader.local(directory.root),
            RecordingJudges(FailingJudge()),
        )

        result = runner.run()

        assert result.failures == (
            "enum-usage a string: not judged: "
            "JudgeError: gemini failed with 502: upstream request failed",
        )

    def test_eval_for_an_unknown_rule_is_reported_as_a_problem(
        self, directory, make_rule_eval_case
    ):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump(
                {
                    "name": "enum-usge",
                    "cases": [make_rule_eval_case().model_dump(mode="json", exclude_defaults=True)],
                }
            ),
        )
        runner = JudgeEvalRunner(
            directory.root,
            RulesetLoader.local(directory.root),
            RecordingJudges(RecordingJudge()),
        )

        result = runner.run()

        assert result == JudgeEvalResult(
            checks=ValidationResult(
                problems=(".codeguard/rule-evals/enum-usage.yaml: no judge rule enum-usge",)
            )
        )

    def test_selected_case_name_judges_only_the_cases_holding_it(
        self, directory, make_rule_eval_case
    ):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump(
                {
                    "cases": [
                        make_rule_eval_case(expected_output__outcome="invalid").model_dump(
                            mode="json", exclude_defaults=True
                        ),
                        make_rule_eval_case(
                            name="the member", inputs__after="ship(status=Status.SHIPPED)\n"
                        ).model_dump(mode="json", exclude_defaults=True),
                    ]
                }
            ),
        )
        runner = JudgeEvalRunner(
            directory.root,
            RulesetLoader.local(directory.root),
            RecordingJudges(RecordingJudge()),
            selection=EvalSelection(cases=("member",)),
        )

        result = runner.run()

        assert [case.name for report in result.reports for case in report.cases] == ["the member"]

    def test_rule_not_selected_is_neither_judged_nor_reported(self, directory, make_rule_eval_case):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump(
                {"cases": [make_rule_eval_case().model_dump(mode="json", exclude_defaults=True)]}
            ),
        )
        judges = RecordingJudges(RecordingJudge())
        runner = JudgeEvalRunner(
            directory.root,
            RulesetLoader.local(directory.root),
            judges,
            selection=EvalSelection(rules=frozenset({"other-rule"})),
        )

        result = runner.run()

        assert result == JudgeEvalResult()
        assert judges.created == []

    def test_case_names_lists_each_judge_rule_s_cases(self, directory, make_rule_eval_case):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump(
                {
                    "cases": [
                        make_rule_eval_case(expected_output__outcome="invalid").model_dump(
                            mode="json", exclude_defaults=True
                        ),
                        make_rule_eval_case(
                            name="the member", inputs__after="ship(status=Status.SHIPPED)\n"
                        ).model_dump(mode="json", exclude_defaults=True),
                    ]
                }
            ),
        )
        runner = JudgeEvalRunner(
            directory.root,
            RulesetLoader.local(directory.root),
            RecordingJudges(RecordingJudge()),
        )

        names = runner.case_names()

        assert names == {"enum-usage": ("a string", "the member")}

    def test_judge_reason_is_reported_for_each_judged_case(
        self, directory, make_rule_eval_case, make_verdict
    ):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump(
                {"cases": [make_rule_eval_case().model_dump(mode="json", exclude_defaults=True)]}
            ),
        )
        verdict = make_verdict(reason="The call passes a string.")
        runner = JudgeEvalRunner(
            directory.root,
            RulesetLoader.local(directory.root),
            RecordingJudges(RecordingJudge(verdict)),
        )

        result = runner.run()

        assert result.reasons == ("enum-usage a string: The call passes a string.",)

    def test_eval_without_cases_fails_as_no_case_evaluated(self, directory):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(".codeguard/rule-evals/enum-usage.yaml", yaml.safe_dump({"cases": []}))
        runner = JudgeEvalRunner(
            directory.root,
            RulesetLoader.local(directory.root),
            RecordingJudges(RecordingJudge()),
        )

        result = runner.run()

        assert result.failures == ("enum-usage: no case was evaluated",)

    def test_rule_with_no_case_selected_is_left_out(self, directory, make_rule_eval_case):
        directory.write(".codeguard/rules/judge/enum-usage.md", ENUM_RULE)
        directory.write(".codeguard/bindings/enum-usage.yaml", ENUM_BINDING)
        directory.write(
            ".codeguard/rule-evals/enum-usage.yaml",
            yaml.safe_dump(
                {"cases": [make_rule_eval_case().model_dump(mode="json", exclude_defaults=True)]}
            ),
        )
        runner = JudgeEvalRunner(
            directory.root,
            RulesetLoader.local(directory.root),
            RecordingJudges(RecordingJudge()),
            selection=EvalSelection(cases=("member",)),
        )

        result = runner.run()

        assert result == JudgeEvalResult()
