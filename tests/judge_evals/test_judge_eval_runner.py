import re
import subprocess
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

import pytest
from factories.diagnostic import MakeViolation
from git_repo import GitRepo
from recording_judge import FailingJudge, RecordingJudge, RecordingJudges

from codeguard.config import ConfigError, JudgeModel, JudgeProvider, RulesetLoader
from codeguard.judge_evals import EvalSelection, JudgeEvalResult, JudgeEvalRunner, JudgeFactory
from codeguard.review import Judge, Judgement, JudgeRequest, Skill, Verdict
from codeguard.rule_tests import RuleTestResult

FIXTURES = Path(__file__).parent / "fixtures"
ENUM_SKILL = "# Enum usage\n\nPass the enum member, never a bare literal.\n"
EVAL_FILE = ".codeguard/rule-evals/enum-usage.yaml"


def copy_fixture(repo: GitRepo, fixture: str, path: str) -> None:
    repo.write(f".codeguard/{path}", (FIXTURES / fixture).read_text())


@dataclass(frozen=True)
class EnumRule:
    repo: GitRepo

    def bind(self, binding: str) -> None:
        copy_fixture(self.repo, f"bindings/{binding}", "bindings/enum-usage.yaml")

    def evaluate(self, rule_eval: str, as_file: str = "enum-usage.yaml") -> None:
        copy_fixture(self.repo, f"rule-evals/{rule_eval}", f"rule-evals/{as_file}")

    def run(
        self,
        judges: JudgeFactory,
        repeat: int = 1,
        selection: EvalSelection = EvalSelection(),
        model: JudgeModel | None = None,
    ) -> JudgeEvalResult:
        return self.runner(judges, repeat, selection, model).run()

    def runner(
        self,
        judges: JudgeFactory,
        repeat: int = 1,
        selection: EvalSelection = EvalSelection(),
        model: JudgeModel | None = None,
    ) -> JudgeEvalRunner:
        loader = RulesetLoader.local(self.repo.root)
        return JudgeEvalRunner(
            self.repo.root, loader, judges, 0.9, repeat=repeat, selection=selection, model=model
        )

    def judged_with(self, verdict: Verdict) -> JudgeEvalResult:
        return self.run(RecordingJudges(RecordingJudge(verdict)))


@pytest.fixture
def enum_rule(repo) -> EnumRule:
    copy_fixture(repo, "skills/enum-usage/SKILL.md", "skills/enum-usage/SKILL.md")
    rule = EnumRule(repo)
    rule.bind("any-trigger.yaml")
    return rule


@dataclass
class ReadingJudges:
    judged: list[str]

    def __call__(self, root: Path, model: JudgeModel) -> Judge:
        self.judged.append((root / "status.py").read_text())
        return RecordingJudge()


@dataclass
class ListingJudges:
    listed: list[list[str]]

    def __call__(self, root: Path, model: JudgeModel) -> Judge:
        self.listed.append(sorted(git(root, "ls-files", "--cached", "--others").split()))
        return RecordingJudge()


@dataclass
class StatusJudges:
    statuses: list[str]

    def __call__(self, root: Path, model: JudgeModel) -> Judge:
        self.statuses.append(git(root, "status", "--porcelain", "--untracked-files=all"))
        return RecordingJudge()


def git(directory: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=directory, check=True, capture_output=True, text=True
    ).stdout


class TestJudgeEvalRunner:
    def test_judges_the_file_after_each_judged_edit(self, enum_rule):
        enum_rule.evaluate("string-replaces-member.yaml")
        judges = ReadingJudges([])

        enum_rule.run(judges)

        assert sorted(judges.judged) == [
            "ship(status='shipped')\n",
            "ship(status=Status.SHIPPED)\n",
        ]

    def test_judges_the_case_file_with_the_rule_skill(self, enum_rule):
        enum_rule.evaluate("string-is-valid.yaml")
        judges = RecordingJudges(RecordingJudge())

        enum_rule.run(judges)

        assert judges.judge.received == [
            JudgeRequest(
                Skill(name="enum-usage", text=ENUM_SKILL),
                "module.py",
                "+     1\tship(status='shipped')\n",
            )
        ]

    def test_each_case_is_judged_in_a_repository_holding_its_files(self, enum_rule):
        enum_rule.evaluate("cases-in-different-files.yaml")
        judges = ListingJudges([])

        enum_rule.run(judges)

        assert sorted(judges.listed) == [
            ["cancelling.py"],
            ["shipping/__init__.py", "shipping/ship.py"],
        ]

    def test_unchanged_files_are_committed_and_left_out_of_the_change(self, enum_rule):
        enum_rule.evaluate("edit-beside-an-unchanged-file.yaml")
        judges = StatusJudges([])

        enum_rule.run(judges)

        assert judges.statuses == [" M shipping/ship.py\n"]

    def test_judges_only_the_function_an_edit_changes(self, enum_rule):
        enum_rule.evaluate("edit-in-the-second-function.yaml")
        judges = RecordingJudges(RecordingJudge())

        enum_rule.run(judges)

        assert judges.judge.received == [
            JudgeRequest(
                Skill(name="enum-usage", text=ENUM_SKILL),
                "status.py",
                "      5\tdef cancel_order():\n"
                "-     6\t    cancel(status=Status.CANCELLED)\n"
                "+     6\t    cancel(status='cancelled')\n",
            )
        ]

    def test_judges_with_the_model_the_binding_names(self, enum_rule):
        enum_rule.bind("gemini-model.yaml")
        enum_rule.evaluate("string-is-valid.yaml")
        judges = RecordingJudges(RecordingJudge())

        enum_rule.run(judges)

        assert [creation.model for creation in judges.created] == [
            JudgeModel(provider=JudgeProvider.GEMINI, name="gemini-3.1-pro-preview")
        ]

    def test_judges_with_the_given_model_instead_of_the_binding_s(self, enum_rule):
        enum_rule.bind("haiku-model.yaml")
        enum_rule.evaluate("string-is-valid.yaml")
        judges = RecordingJudges(RecordingJudge())
        gemini = JudgeModel(provider=JudgeProvider.GEMINI, name="gemini-3.1-pro-preview")

        result = enum_rule.run(judges, model=gemini)

        assert [creation.model for creation in judges.created] == [gemini]
        assert [report.name for report in result.reports] == [
            "enum-usage on gemini-3.1-pro-preview"
        ]

    def test_reports_one_experiment_per_rule_named_after_the_rule_and_model(self, enum_rule):
        enum_rule.bind("haiku-model.yaml")
        enum_rule.evaluate("string-is-valid.yaml")

        result = enum_rule.judged_with(Verdict(violations=()))

        assert [(report.dataset_name, report.name) for report in result.reports] == [
            ("enum-usage", "enum-usage on claude-haiku-5-5")
        ]

    def test_records_the_model_rule_version_and_codeguard_version(self, enum_rule):
        enum_rule.bind("haiku-model.yaml")
        enum_rule.evaluate("string-is-valid.yaml")

        result = enum_rule.judged_with(Verdict(violations=()))

        metadata = result.reports[0].experiment_metadata
        assert metadata is not None
        assert {name: metadata[name] for name in ("provider", "model", "codeguard_version")} == {
            "provider": "claude-cli",
            "model": "claude-haiku-5-5",
            "codeguard_version": version("codeguard"),
        }
        assert re.fullmatch("[0-9a-f]{12}", metadata["rule_version"])

    def test_rule_version_changes_with_the_skill(self, enum_rule, repo):
        enum_rule.evaluate("string-is-valid.yaml")
        before = enum_rule.judged_with(Verdict(violations=())).reports[0].experiment_metadata
        repo.write(
            ".codeguard/skills/enum-usage/SKILL.md",
            f"---\nname: enum-usage\n---\n{ENUM_SKILL}Also pass members to compare.\n",
        )

        after = enum_rule.judged_with(Verdict(violations=())).reports[0].experiment_metadata

        assert before is not None and after is not None
        assert before["rule_version"] != after["rule_version"]

    def test_confident_violation_passes_an_invalid_case(self, enum_rule, make_violation):
        enum_rule.evaluate("string-is-invalid.yaml")

        result = enum_rule.judged_with(
            Verdict(violations=(make_violation(file="module.py", confidence=0.9),))
        )

        assert result.passed

    def test_violation_outside_the_triggers_fails_with_the_kinds_on_its_line(
        self, enum_rule, make_violation
    ):
        enum_rule.bind("class-header-and-string-literal-triggers.yaml")
        enum_rule.evaluate("string-then-number-is-invalid.yaml")

        result = enum_rule.judged_with(
            Verdict(violations=(make_violation(file="module.py", line=2, confidence=0.9),))
        )

        assert result.failures == (
            "enum-usage passes a string: violation on line 2 is outside the "
            "triggers class-header, string-literal\n"
            "  Add one of the kinds on that line to triggers in its binding: "
            "code, module-statement, number-literal",
        )

    def test_violation_outside_the_triggers_in_a_valid_case_fails_only_as_a_false_positive(
        self, enum_rule, make_violation
    ):
        enum_rule.bind("string-literal-trigger.yaml")
        enum_rule.evaluate("string-then-number-is-valid.yaml")

        result = enum_rule.judged_with(
            Verdict(violations=(make_violation(file="module.py", line=2, confidence=0.9),))
        )

        assert [failure.split("\n")[0] for failure in result.failures] == [
            "enum-usage passes a string: expected outcome valid, got outcome invalid"
        ]

    def test_dataset_without_cases_fails_with_its_name(self, enum_rule):
        enum_rule.evaluate("without-cases.yaml")

        result = enum_rule.judged_with(Verdict(violations=()))

        assert not result.passed
        assert result.failures == ("enum-usage: no case was evaluated",)

    def test_violation_inside_the_triggers_passes(self, enum_rule, make_violation):
        enum_rule.bind("string-literal-trigger.yaml")
        enum_rule.evaluate("string-is-invalid.yaml")

        result = enum_rule.judged_with(
            Verdict(violations=(make_violation(file="module.py", confidence=0.9),))
        )

        assert result.passed

    def test_unconfident_violation_fails_an_invalid_case(self, enum_rule, make_violation):
        enum_rule.evaluate("string-is-invalid.yaml")
        violation = make_violation(file="module.py", message="Pass the member.", confidence=0.7)

        result = enum_rule.judged_with(Verdict(violations=(violation,)))

        assert result.failures == (
            "enum-usage passes a string: expected outcome invalid, got outcome uncertain\n"
            "  line 1 (0.70): Pass the member.",
        )

    def test_no_violation_fails_an_invalid_case(self, enum_rule):
        enum_rule.evaluate("string-is-invalid.yaml")

        result = enum_rule.judged_with(Verdict(violations=()))

        assert result.failures == (
            "enum-usage passes a string: expected outcome invalid, got outcome valid",
        )

    def test_violation_on_an_unchanged_line_is_dropped_as_a_review_drops_it(
        self, enum_rule, make_violation
    ):
        enum_rule.evaluate("edit-in-the-second-function.yaml")

        result = enum_rule.judged_with(
            Verdict(violations=(make_violation(file="status.py", line=2, confidence=0.9),))
        )

        assert result.failures == (
            "enum-usage passes a string: expected outcome invalid, got outcome valid",
        )

    def test_violation_in_another_file_does_not_pass_an_invalid_case(
        self, enum_rule, make_violation
    ):
        enum_rule.evaluate("string-is-invalid.yaml")

        result = enum_rule.judged_with(Verdict(violations=(make_violation(file="other.py"),)))

        assert result.failures == (
            "enum-usage passes a string: expected outcome invalid, got outcome valid",
        )

    def test_no_violation_passes_a_valid_case(self, enum_rule):
        enum_rule.evaluate("string-is-valid.yaml")

        result = enum_rule.judged_with(Verdict(violations=()))

        assert result.passed

    def test_any_violation_fails_a_valid_case(self, enum_rule, make_violation):
        enum_rule.evaluate("string-is-valid.yaml")
        violation = make_violation(file="module.py", message="Pass the member.", confidence=0.5)

        result = enum_rule.judged_with(Verdict(violations=(violation,)))

        assert result.failures == (
            "enum-usage passes a string: expected outcome valid, got outcome uncertain\n"
            "  line 1 (0.50): Pass the member.",
        )

    def test_case_outside_the_triggers_is_skipped_without_judging(self, enum_rule):
        enum_rule.bind("string-literal-trigger.yaml")
        enum_rule.evaluate("number-only-is-skipped.yaml")
        judges = RecordingJudges(RecordingJudge())

        result = enum_rule.run(judges)

        assert (result.passed, judges.created) == (True, [])

    def test_case_adding_only_blank_lines_is_skipped_without_judging(self, enum_rule):
        enum_rule.evaluate("blank-lines-only.yaml")
        judges = RecordingJudges(RecordingJudge())

        result = enum_rule.run(judges)

        assert result.passed
        assert judges.created == []

    def test_expected_violation_is_checked_only_on_the_fields_it_lists(
        self, enum_rule, make_violation
    ):
        enum_rule.evaluate("violation-without-kinds.yaml")
        violation = make_violation(file="module.py", message="Pass the member.", confidence=0.9)

        result = enum_rule.judged_with(Verdict(violations=(violation,)))

        assert result.passed

    def test_each_expected_violation_is_checked_on_its_own_fields(self, enum_rule, make_violation):
        enum_rule.evaluate("violations-with-and-without-kinds.yaml")
        first = make_violation(file="module.py", line=1, message="Pass the member.", confidence=0.9)
        second = make_violation(
            file="module.py", line=2, message="Pass the member.", confidence=0.9
        )

        result = enum_rule.judged_with(Verdict(violations=(first, second)))

        assert result.passed

    def test_invalid_case_outside_the_triggers_fails_as_skipped(self, enum_rule):
        enum_rule.bind("string-literal-trigger.yaml")
        enum_rule.evaluate("number-only-is-invalid.yaml")

        result = enum_rule.judged_with(Verdict(violations=()))

        assert result.failures == (
            "enum-usage counts: expected outcome invalid, got outcome skipped",
        )

    def test_judge_error_fails_the_case(self, enum_rule):
        enum_rule.evaluate("string-is-invalid.yaml")

        result = enum_rule.run(RecordingJudges(FailingJudge()))

        assert not result.passed
        assert result.failures == (
            "enum-usage passes a string: not judged: "
            "JudgeError: gemini failed with 502: upstream request failed",
        )

    def test_eval_for_an_unknown_rule_fails(self, enum_rule):
        enum_rule.evaluate("named-for-a-misspelled-rule.yaml")

        result = enum_rule.judged_with(Verdict(violations=()))

        assert result == JudgeEvalResult(
            checks=RuleTestResult(problems=(f"{EVAL_FILE}: no judge rule enum-usge",))
        )

    def test_dataset_name_defaults_to_the_file_name(self, enum_rule):
        enum_rule.evaluate("string-is-valid.yaml")

        result = enum_rule.judged_with(Verdict(violations=()))

        assert [report.dataset_name for report in result.reports] == ["enum-usage"]

    def test_eval_file_may_end_in_yml(self, enum_rule):
        enum_rule.evaluate("string-is-valid.yaml", as_file="enum-usage.yml")

        result = enum_rule.judged_with(Verdict(violations=()))

        assert [report.dataset_name for report in result.reports] == ["enum-usage"]

    def test_two_eval_files_naming_one_rule_are_an_error(self, enum_rule, repo):
        enum_rule.evaluate("string-is-valid.yaml")
        enum_rule.evaluate("named-enum-usage.yaml", as_file="more.yaml")

        with pytest.raises(ConfigError) as error:
            enum_rule.judged_with(Verdict(violations=()))

        assert str(error.value) == (
            "a rule has one eval file; remove one of:\n"
            f"  {repo.root / EVAL_FILE}\n"
            f"  {repo.root}/.codeguard/rule-evals/more.yaml"
        )

    def test_codeguard_0_4_eval_file_is_an_error_asking_to_convert_it(self, enum_rule, repo):
        enum_rule.evaluate("codeguard-0.4-format.yml", as_file="enum-usage-eval.yml")

        with pytest.raises(ConfigError) as error:
            enum_rule.judged_with(Verdict(violations=()))

        assert str(error.value) == (
            f"{repo.root}/.codeguard/rule-evals/enum-usage-eval.yml is a codeguard 0.4 rule "
            "eval; convert it to rule-evals/<rule id>.yaml"
        )

    def test_rule_with_a_yaml_and_a_yml_eval_file_is_an_error(self, enum_rule, repo):
        enum_rule.evaluate("string-is-valid.yaml")
        enum_rule.evaluate("string-is-valid.yaml", as_file="enum-usage.yml")

        with pytest.raises(ConfigError) as error:
            enum_rule.judged_with(Verdict(violations=()))

        assert str(error.value) == (
            "a rule has one eval file; remove one of:\n"
            f"  {repo.root / EVAL_FILE}\n"
            f"  {repo.root}/.codeguard/rule-evals/enum-usage.yml"
        )

    @pytest.mark.parametrize(
        ("rule_eval", "error"),
        [
            ("case-without-expected-output.yaml", "cases.0.expected_output: Field required"),
            ("case-without-a-name.yaml", "cases.0.name: Field required"),
            (
                "cases-sharing-a-name.yaml",
                "cases: Value error, cases share a name: passes a string",
            ),
            ("declares-evaluators.yaml", "evaluators: Extra inputs are not permitted"),
            (
                "expects-uncertain.yaml",
                "cases.0.expected_output: Value error, a case expects invalid, valid or "
                "skipped; one the judge can't decide isn't clear enough for a rule eval",
            ),
        ],
    )
    def test_invalid_eval_file_is_an_error(self, enum_rule, repo, rule_eval, error):
        enum_rule.evaluate(rule_eval)

        with pytest.raises(ConfigError) as raised:
            enum_rule.judged_with(Verdict(violations=()))

        assert str(raised.value) == f"{repo.root / EVAL_FILE} is invalid:\n  {error}"


@dataclass(frozen=True)
class FlagsText:
    text: str

    identity = "flags-text"

    def judge(self, request: JudgeRequest) -> Judgement:
        if self.text not in request.changes:
            return Judgement(Verdict(violations=()))
        violation = MakeViolation(file=request.file, message="Rename it.")
        return Judgement(Verdict(violations=(violation,)))


def flagging(text: str) -> JudgeFactory:
    return lambda root, model: FlagsText(text)


class TestRepeats:
    def test_judges_each_case_once_per_repeat(self, enum_rule):
        enum_rule.evaluate("string-is-valid.yaml")
        judge = RecordingJudge()

        enum_rule.run(RecordingJudges(judge), repeat=3)

        assert [request.file for request in judge.received] == ["module.py"] * 3

    def test_failing_run_is_numbered(self, enum_rule):
        enum_rule.evaluate("string-is-valid.yaml")

        result = enum_rule.run(flagging("ship"), repeat=2)

        assert sorted(result.failures) == [
            f"enum-usage passes a string [{run}/2]: expected outcome valid, got outcome "
            "invalid\n  line 1 (1.00): Rename it."
            for run in (1, 2)
        ]


class TestSelection:
    def test_judges_only_the_cases_whose_name_has_the_text(self, enum_rule):
        enum_rule.evaluate("cases-in-different-files.yaml")
        judges = ListingJudges([])

        result = enum_rule.run(judges, selection=EvalSelection(cases=("member",)))

        assert judges.listed == [["cancelling.py"]]
        assert [case.name for report in result.reports for case in report.cases] == [
            "passes the member"
        ]

    def test_judges_nothing_of_a_rule_not_selected(self, enum_rule):
        enum_rule.evaluate("string-is-valid.yaml")
        judges = RecordingJudges(RecordingJudge())

        result = enum_rule.run(judges, selection=EvalSelection(rules=frozenset({"other-rule"})))

        assert (result, judges.created) == (JudgeEvalResult(), [])

    def test_unknown_eval_of_a_rule_not_selected_is_not_reported(self, enum_rule):
        enum_rule.evaluate("named-for-a-misspelled-rule.yaml")

        result = enum_rule.run(
            RecordingJudges(RecordingJudge()), selection=EvalSelection(rules=frozenset({"x"}))
        )

        assert result == JudgeEvalResult()

    def test_rule_with_no_case_selected_is_left_out(self, enum_rule):
        enum_rule.evaluate("string-is-valid.yaml")

        result = enum_rule.run(
            RecordingJudges(RecordingJudge()), selection=EvalSelection(cases=("member",))
        )

        assert result == JudgeEvalResult()

    def test_lists_the_case_names_of_each_judge_rule(self, enum_rule):
        enum_rule.evaluate("cases-in-different-files.yaml")

        names = enum_rule.runner(RecordingJudges(RecordingJudge())).case_names()

        assert names == {"enum-usage": ("passes a string", "passes the member")}

    def test_judge_rule_without_an_eval_has_no_case_names(self, enum_rule):
        names = enum_rule.runner(RecordingJudges(RecordingJudge())).case_names()

        assert names == {"enum-usage": ()}


class TestWithoutJudgeEvals:
    def test_reports_nothing_without_loading_bindings(self, repo):
        copy_fixture(repo, "bindings/misspelled-paths-key.yaml", "bindings/broken.yaml")
        judges = RecordingJudges(RecordingJudge())

        result = JudgeEvalRunner(repo.root, RulesetLoader.local(repo.root), judges, 0.9).run()

        assert result == JudgeEvalResult()
