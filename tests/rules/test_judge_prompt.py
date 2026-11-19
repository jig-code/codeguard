import shutil
import subprocess
import sys
from contextlib import AbstractContextManager
from pathlib import Path

import pytest
import yaml
from spans import finished_span_attributes

from codeguard.config import (
    FileEdit,
    JudgeChoice,
    JudgeModel,
    JudgeProvider,
    Outcome,
    RuleEvalCase,
    RuleEvalReader,
)
from codeguard.packages import MANIFEST_FILE, Package
from codeguard.repository import LineScopes, WorkingTree
from codeguard.review import Bindings, Category, Review
from codeguard.rules import Rules, judges

EVALS = Path(__file__).parents[2] / "evals" / "judge"
CASES = [
    pytest.param(rule_eval.name, case, id=f"{rule_eval.name}: {case.name}")
    for _, rule_eval in RuleEvalReader(EVALS / "python").read()
    for case in rule_eval.cases
]
JUDGED_CASES = [
    case for case in CASES if case.values[1].expected_output.outcome is not Outcome.SKIPPED
]


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "run" in metafunc.fixturenames:
        runs: int = metafunc.config.getoption("llm_runs")
        metafunc.parametrize("run", range(1, runs + 1), ids=lambda run: f"{run}/{runs}")


@pytest.fixture
def judge_override(request: pytest.FixtureRequest) -> JudgeChoice:
    provider: JudgeProvider | None = request.config.getoption("judge_provider")
    if provider is None:
        return JudgeChoice()
    model: str | None = request.config.getoption("judge_model") or provider.default_model
    return JudgeChoice(provider=provider, model=model)


@pytest.fixture
def judged_evals(judge_override: JudgeChoice, tmp_path: Path) -> Path:
    if judge_override.provider is None:
        return EVALS
    evals = shutil.copytree(EVALS, tmp_path / "evals")
    manifest = evals / MANIFEST_FILE
    judge = judge_override.model_dump(mode="json", exclude_none=True)
    manifest.write_text(yaml.safe_dump(yaml.safe_load(manifest.read_text()) | {"judge": judge}))
    return evals


@pytest.fixture(autouse=True)
def judgement_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(judges, "_JUDGEMENT_CACHE_DIR", tmp_path / "judgements")


class TestJudgePrompt:
    @pytest.mark.parametrize("judge_override", [JudgeChoice(provider=JudgeProvider.CLAUDE_CLI)])
    def test_claude_cli_override_judges_with_the_cli_default_model(self, judged_evals: Path):
        ruleset = Package.load(judged_evals).ruleset_loader("python").load()

        bindings = Bindings.from_rulesets([ruleset])

        assert {binding.model for binding in bindings} == {
            JudgeModel(provider=JudgeProvider.CLAUDE_CLI)
        }

    def test_public_interface_valid_fixture_loads_from_its_consumer(self):
        case = next(
            parameter.values[1]
            for parameter in CASES
            if parameter.values[0] == "package-public-interface"
            and parameter.values[1].expected_output.outcome is Outcome.VALID
        )
        module = case.inputs.file.removesuffix(".py").replace("/", ".")

        with WorkingTree.temporary(case.inputs.before_files(), case.inputs.after_files()) as tree:
            result = subprocess.run(
                [sys.executable, "-c", f"__import__({module!r})"],
                cwd=tree.root,
                capture_output=True,
                text=True,
                check=False,
            )

        assert result.returncode == 0, result.stderr

    @pytest.mark.parametrize(("rule", "case"), CASES)
    def test_triggers_fire_on_each_case_the_judge_sees(self, rule: str, case: RuleEvalCase):
        with _case_tree(EVALS, rule, case.inputs) as working_tree:
            plan = Rules(working_tree).plan(LineScopes.at(working_tree).changed_lines("HEAD"))

        triggered = [call.file for call in plan.calls if call.triggered]
        judged = case.expected_output.outcome is not Outcome.SKIPPED
        assert triggered == ([case.inputs.file] if judged else [])

    @pytest.mark.llm
    @pytest.mark.usefixtures("this_machines_gemini_sign_in")
    @pytest.mark.parametrize(("rule", "case"), JUDGED_CASES)
    def test_review_reaches_each_case_verdict(
        self, rule: str, case: RuleEvalCase, run: int, judged_evals: Path, capfire
    ):
        with _case_tree(judged_evals, rule, case.inputs) as working_tree:
            review = Rules(working_tree).review(LineScopes.at(working_tree).changed_lines("HEAD"))

        listing = "\n".join(map(str, review.diagnostics))
        telemetry = finished_span_attributes(capfire, "codex judges {rule} on {file}")
        if telemetry:
            listing += f"\nJudge telemetry: {telemetry!r}"
        errors = [
            diagnostic
            for diagnostic in review.diagnostics
            if diagnostic.category is Category.JUDGE_ERROR
        ]
        assert errors == [], listing
        assert _outcome(review) is case.expected_output.outcome, listing


def _case_tree(evals: Path, rule: str, inputs: FileEdit) -> AbstractContextManager[WorkingTree]:
    config = yaml.safe_dump(
        {
            "packages": [
                {"kind": "path", "path": str(evals), "rulesets": {"python": {"include": [rule]}}}
            ]
        }
    )
    return WorkingTree.temporary(
        {".codeguard/config.yaml": config, **inputs.before_files()},
        {".codeguard/config.yaml": config, **inputs.after_files()},
    )


def _outcome(review: Review) -> Outcome:
    if review.blocks:
        return Outcome.INVALID
    return Outcome.UNCERTAIN if review.diagnostics else Outcome.VALID
