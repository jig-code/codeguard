from general_rule import (
    EVAL,
    GENERAL_SKILL,
    PYTHON_CASE,
    PYTHON_SUPPLEMENT,
    RULE,
    SKILL_DIR,
    TYPESCRIPT_CASE,
    case,
    write_general_rule,
)
from recording_judge import RecordingJudge, RecordingJudges

from codeguard.config import RulesetLoader
from codeguard.judge_evals import EvalCoverage, JudgeEvalRunner
from codeguard.review import Bindings
from codeguard.rule_tests import RuleTestResult, TriggerTestRunner


def binding(repo):
    (bound,) = Bindings.from_rulesets([RulesetLoader.local(repo.root).load()])
    return bound


class TestGeneralRuleSkill:
    def test_a_file_is_judged_with_the_skill_and_its_language_supplement(self, repo):
        write_general_rule(repo)

        assert binding(repo).skill_for("orders.py").text == f"{GENERAL_SKILL}\n{PYTHON_SUPPLEMENT}"

    def test_a_language_without_a_supplement_gets_the_skill_alone(self, repo):
        write_general_rule(repo)

        assert binding(repo).skill_for("orders.ts").text == GENERAL_SKILL

    def test_a_supplement_changes_only_its_language_version(self, repo):
        write_general_rule(repo)
        before = binding(repo)
        repo.write(f"{SKILL_DIR}/python.md", "## In Python\n\nA settings module.\n")

        after = binding(repo)

        assert after.version_for("python") != before.version_for("python")
        assert after.version_for("typescript") == before.version_for("typescript")

    def test_the_skill_changes_every_language_version(self, repo):
        write_general_rule(repo)
        before = binding(repo)
        repo.write(f"{SKILL_DIR}/SKILL.md", "# Knowledge stated once, reworded\n")

        after = binding(repo)

        assert after.version_for("python") != before.version_for("python")
        assert after.version_for("typescript") != before.version_for("typescript")


class TestGeneralRuleEvals:
    def run(self, repo, judge):
        loader = RulesetLoader.local(repo.root)
        return JudgeEvalRunner(repo.root, loader, RecordingJudges(judge), 0.9).run()

    def test_each_language_is_reported_on_its_own(self, repo):
        write_general_rule(repo)
        repo.write(EVAL, f"cases:\n{PYTHON_CASE}{TYPESCRIPT_CASE}")

        result = self.run(repo, RecordingJudge())

        assert sorted(report.name for report in result.reports) == [
            f"{RULE} (python) on claude-sonnet-5-5",
            f"{RULE} (typescript) on claude-sonnet-5-5",
        ]

    def test_each_case_is_judged_with_its_language_supplement(self, repo):
        write_general_rule(repo)
        repo.write(EVAL, f"cases:\n{PYTHON_CASE}{TYPESCRIPT_CASE}")
        judge = RecordingJudge()

        self.run(repo, judge)

        assert sorted(request.skill.text for request in judge.received) == [
            GENERAL_SKILL,
            f"{GENERAL_SKILL}\n{PYTHON_SUPPLEMENT}",
        ]

    def test_a_single_language_rule_keeps_one_report(self, repo):
        write_general_rule(repo, binding='paths: ["**/*.py"]\ntriggers: [string-literal]\n')
        repo.write(EVAL, f"cases:\n{PYTHON_CASE}")

        result = self.run(repo, RecordingJudge())

        assert [report.name for report in result.reports] == [f"{RULE} on claude-sonnet-5-5"]


class TestGeneralRuleCoverage:
    def test_each_language_the_paths_name_needs_an_invalid_case(self, repo):
        write_general_rule(repo)
        repo.write(EVAL, f"cases:\n{PYTHON_CASE}")

        result = EvalCoverage(RulesetLoader.local(repo.root)).run()

        assert result == RuleTestResult(
            problems=(f"{RULE} (typescript): no eval with an invalid case",)
        )

    def test_a_case_in_each_language_passes(self, repo):
        write_general_rule(repo)
        repo.write(EVAL, f"cases:\n{PYTHON_CASE}{TYPESCRIPT_CASE}")

        assert EvalCoverage(RulesetLoader.local(repo.root)).run() == RuleTestResult()


class TestGeneralRuleTriggers:
    def test_a_case_in_a_language_without_change_kinds_fires_every_trigger(self, repo):
        write_general_rule(repo)
        repo.write(EVAL, f"cases:\n{PYTHON_CASE}{TYPESCRIPT_CASE}")

        result = TriggerTestRunner(repo.root, RulesetLoader.local(repo.root)).run()

        assert result == RuleTestResult()

    def test_a_skipped_case_in_such_a_language_fails(self, repo):
        write_general_rule(repo)
        repo.write(
            EVAL, "cases:\n" + case("renames a script", "orders.ts", "let s = 1;", "skipped")
        )

        result = TriggerTestRunner(repo.root, RulesetLoader.local(repo.root)).run()

        assert result == RuleTestResult(
            problems=(
                f"{EVAL} renames a script: orders.ts has no change kinds, "
                f"so every {RULE} trigger fires on it",
            )
        )
