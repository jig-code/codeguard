import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from diskcache import Cache
from factories.classification import MakeFileClassification
from factories.diagnostic import MakeDiagnostic, MakeViolation
from factories.judge_request import MakeJudgeRequest
from factories.line_range import MakeLineRange
from factories.rule_eval import (
    MakeEditCase,
    MakeEditReview,
    MakeEvaluatorContext,
    MakeJudgedViolation,
    MakeRuleEvalCase,
    MakeVerdict,
)
from factories.ruleset import MakeBindingConfig, MakeRuleset
from factories.skill import MakeBinding, MakeSkill
from git_repo import GitRepo
from pytest_factoryboy import register

from codeguard.config import JudgeProvider

register(MakeLineRange)
register(MakeDiagnostic)
register(MakeViolation)
register(MakeSkill)
register(MakeBinding)
register(MakeBindingConfig)
register(MakeRuleset)
register(MakeJudgeRequest)
register(MakeVerdict)
register(MakeEditCase)
register(MakeJudgedViolation)
register(MakeEditReview)
register(MakeEvaluatorContext)
register(MakeRuleEvalCase)
register(MakeFileClassification)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--llm-runs",
        type=int,
        default=3,
        help="Run each llm test this many times. Default: 3.",
    )
    parser.addoption(
        "--judge-provider",
        type=JudgeProvider,
        choices=list(JudgeProvider),
        help="Judge the llm tests' fixture cases with this provider instead of their bindings'.",
    )
    parser.addoption(
        "--judge-model",
        help="The model --judge-provider judges with. Default: the provider's default model; "
        "none for claude-cli, so the claude CLI runs its own default.",
    )


@pytest.fixture(autouse=True)
def no_telemetry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOGFIRE_TOKEN", raising=False)
    monkeypatch.setenv("LOGFIRE_IGNORE_NO_CONFIG", "1")


@pytest.fixture(autouse=True)
def committed_config(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CODEGUARD_CONFIG", raising=False)
    judges_with_this_machines_gemini = request.node.get_closest_marker("llm") is not None
    for name in list(os.environ):
        if name.startswith("CODEGUARD_JUDGE__") and not (
            judges_with_this_machines_gemini and name.startswith("CODEGUARD_JUDGE__GEMINI__")
        ):
            monkeypatch.delenv(name)


@pytest.fixture
def fake_cli_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEGUARD_TEST_CLI_CONFIG", str(tmp_path / "fake-cli-response.json"))


@pytest.fixture
def git_repo(tmp_path: Path) -> GitRepo:
    return GitRepo.init(tmp_path.resolve())


@pytest.fixture
def repo(tmp_path: Path) -> GitRepo:
    git_repo = GitRepo.init(tmp_path.resolve())
    git_repo.write(
        ".codeguard/rules/pattern/no-print.yml",
        "id: no-print\n"
        "language: python\n"
        "severity: error\n"
        "message: Use logging, not print.\n"
        "note: |\n"
        "  print bypasses log levels.\n"
        "  Call logger.info instead.\n"
        "metadata:\n"
        "  why: Print output skips the log levels and handlers production reads.\n"
        "rule:\n"
        "  pattern: print($$$ARGS)\n",
    )
    git_repo.write(
        ".codeguard/rules/pattern/no-breakpoint.yml",
        "id: no-breakpoint\n"
        "language: python\n"
        "severity: warning\n"
        "message: Remove breakpoint().\n"
        "metadata:\n"
        "  why: A breakpoint left in the code stops a run that nobody is watching.\n"
        "rule:\n"
        "  pattern: breakpoint()\n",
    )
    git_repo.commit("Add rules")
    return git_repo


@pytest.fixture
def store(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Cache]:
    with Cache(tmp_path_factory.mktemp("judgements")) as cache:
        yield cache
