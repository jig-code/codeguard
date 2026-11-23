import os
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from diskcache import Cache
from factories.changed_lines import MakeChangedLines, MakeNewFileChangedLines
from factories.classification import MakeFileClassification
from factories.diagnostic import MakeDiagnostic, MakeViolation
from factories.judge_request import MakeJudgeRequest
from factories.judge_rule import MakeBinding, MakeJudgeRule
from factories.line_range import MakeLineRange
from factories.rule_eval import (
    MakeEditVerdict,
    MakeEvaluatorContext,
    MakeFileEdit,
    MakeJudgedViolation,
    MakeRuleEvalCase,
    MakeVerdict,
)
from factories.ruleset import MakeBindingConfig, MakeRuleset
from fake_cli import FAKE_CLAUDE
from git_repo import Directory, GitRepo
from pytest_factoryboy import register

from codeguard.config import JudgeProvider
from codeguard.rules import judges

PROJECT_CODEGUARD = Path(__file__).parent / "data/project-codeguard"

register(MakeLineRange)
register(MakeDiagnostic)
register(MakeViolation)
register(MakeJudgeRule)
register(MakeBinding)
register(MakeBindingConfig)
register(MakeRuleset)
register(MakeJudgeRequest)
register(MakeVerdict)
register(MakeFileEdit)
register(MakeJudgedViolation)
register(MakeEditVerdict)
register(MakeEvaluatorContext)
register(MakeRuleEvalCase)
register(MakeFileClassification)
register(MakeChangedLines)
register(MakeNewFileChangedLines, _name="new_file_changed_lines")


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
        help="Judge the llm tests' fixture cases with this provider instead of their package's.",
    )
    parser.addoption(
        "--judge-model",
        help="The model --judge-provider judges with. Default: the provider's default model; "
        "none for claude-cli, so the claude CLI runs its own default.",
    )


_THIS_MACHINES_GEMINI_SETTINGS = {
    name: value
    for name, value in os.environ.items()
    if name.startswith("CODEGUARD_JUDGE__GEMINI__")
}


@pytest.fixture(autouse=True)
def no_telemetry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOGFIRE_TOKEN", raising=False)
    monkeypatch.setenv("LOGFIRE_IGNORE_NO_CONFIG", "1")


@pytest.fixture(autouse=True)
def committed_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CODEGUARD_CONFIG", raising=False)
    for name in list(os.environ):
        if name.startswith("CODEGUARD_JUDGE__"):
            monkeypatch.delenv(name)


@pytest.fixture
def this_machines_gemini_sign_in(committed_config: None, monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in _THIS_MACHINES_GEMINI_SETTINGS.items():
        monkeypatch.setenv(name, value)


@pytest.fixture
def fake_cli_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEGUARD_TEST_CLI_CONFIG", str(tmp_path / "fake-cli-response.json"))


@pytest.fixture
def fake_claude_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", f"{FAKE_CLAUDE.parent}{os.pathsep}{os.environ['PATH']}")


@pytest.fixture
def judgement_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(judges, "_JUDGEMENT_CACHE_DIR", tmp_path / "judgements")


@pytest.fixture
def directory(tmp_path: Path) -> Directory:
    return Directory(tmp_path.resolve())


@pytest.fixture
def git_repo(tmp_path: Path) -> GitRepo:
    return GitRepo.init(tmp_path.resolve())


@pytest.fixture
def repo(tmp_path: Path) -> GitRepo:
    git_repo = GitRepo.init(tmp_path.resolve())
    shutil.copytree(PROJECT_CODEGUARD, git_repo.root / ".codeguard")
    git_repo.commit("Add rules")
    return git_repo


@pytest.fixture
def store(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Cache]:
    with Cache(tmp_path_factory.mktemp("judgements")) as cache:
        yield cache
