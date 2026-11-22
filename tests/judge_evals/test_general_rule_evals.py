import yaml
from general_rule import (
    BINDING,
    BOTH_LANGUAGES,
    EVAL,
    GENERAL_RULE,
    PYTHON_CASE,
    RULE,
    RULE_FILE,
    TYPESCRIPT_CASE,
    case,
)
from recording_judge import RecordingJudge, RecordingJudges

from codeguard.config import RulesetLoader
from codeguard.judge_evals import EvalCoverage, JudgeEvalRunner
from codeguard.rule_validation import TriggerCaseValidation, ValidationResult


class TestGeneralRuleVersion:
    def test_rewording_the_rule_changes_the_rule_version(self, make_binding):
        before = make_binding(judge_rule__text=GENERAL_RULE)
        after = make_binding(judge_rule__text="# Knowledge stated once, reworded\n")

        assert after.version != before.version


class TestGeneralRuleEvals:
    def run(self, directory, judge):
        loader = RulesetLoader.local(directory.root)
        return JudgeEvalRunner(directory.root, loader, RecordingJudges(judge)).run()

    def test_each_language_is_reported_on_its_own(self, directory):
        directory.write(RULE_FILE, GENERAL_RULE)
        directory.write(BINDING, yaml.safe_dump({"rule": RULE} | BOTH_LANGUAGES))
        directory.write(EVAL, yaml.safe_dump({"cases": [PYTHON_CASE, TYPESCRIPT_CASE]}))

        result = self.run(directory, RecordingJudge())

        assert sorted(report.name for report in result.reports) == [
            f"{RULE} (python) on claude-cli's default model",
            f"{RULE} (typescript) on claude-cli's default model",
        ]


class TestGeneralRuleCoverage:
    def test_each_language_the_paths_name_needs_an_invalid_case(self, directory):
        directory.write(RULE_FILE, GENERAL_RULE)
        directory.write(BINDING, yaml.safe_dump({"rule": RULE} | BOTH_LANGUAGES))
        directory.write(EVAL, yaml.safe_dump({"cases": [PYTHON_CASE]}))

        result = EvalCoverage(RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult(
            problems=(f"{RULE} (typescript): no eval with an invalid case",)
        )

    def test_a_case_in_each_language_passes(self, directory):
        directory.write(RULE_FILE, GENERAL_RULE)
        directory.write(BINDING, yaml.safe_dump({"rule": RULE} | BOTH_LANGUAGES))
        directory.write(EVAL, yaml.safe_dump({"cases": [PYTHON_CASE, TYPESCRIPT_CASE]}))

        assert EvalCoverage(RulesetLoader.local(directory.root)).run() == ValidationResult()


class TestGeneralRuleTriggers:
    def test_a_case_in_a_language_without_change_kinds_fires_every_trigger(self, directory):
        directory.write(RULE_FILE, GENERAL_RULE)
        directory.write(BINDING, yaml.safe_dump({"rule": RULE} | BOTH_LANGUAGES))
        directory.write(EVAL, yaml.safe_dump({"cases": [PYTHON_CASE, TYPESCRIPT_CASE]}))

        result = TriggerCaseValidation(directory.root, RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult()

    def test_a_skipped_case_in_such_a_language_fails(self, directory):
        directory.write(RULE_FILE, GENERAL_RULE)
        directory.write(BINDING, yaml.safe_dump({"rule": RULE} | BOTH_LANGUAGES))
        directory.write(
            EVAL,
            yaml.safe_dump(
                {"cases": [case("a renamed script", "orders.ts", "let s = 1;", "skipped")]}
            ),
        )

        result = TriggerCaseValidation(directory.root, RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult(
            problems=(
                f"{EVAL} a renamed script: orders.ts has no change kinds, "
                f"so every {RULE} trigger fires on it",
            )
        )
