import importlib.util
import json
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

from codeguard.review import Severity

STOP_SCRIPT = Path(__file__).resolve().parents[3] / "plugin" / "hooks" / "stop.py"


@pytest.fixture(scope="module")
def stop() -> ModuleType:
    spec = importlib.util.spec_from_file_location("stop", STOP_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestReviewResponse:
    def test_blocking_diagnostic_goes_to_the_agent_as_a_required_fix(self, stop, make_diagnostic):
        diagnostic = make_diagnostic()
        review = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout=json.dumps({"diagnostics": [diagnostic.as_json()]}),
            stderr="",
        )

        response = stop.review_response(review)

        assert response == {
            "decision": "block",
            "reason": (
                f"a.py:1: error no-print: Use logging, not print. [{diagnostic.id}]\n"
                "  print bypasses log levels.\n"
                "  Call logger.info instead.\n"
                f"{stop.REQUIRED_FIXES}"
            ),
        }

    def test_warning_goes_to_the_user(self, stop, make_diagnostic):
        warning = make_diagnostic(warning=True)
        review = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps({"diagnostics": [warning.as_json()]}),
            stderr="",
        )

        response = stop.review_response(review)

        assert response == {
            "systemMessage": (
                "codeguard warnings:\n"
                f"a.py:1: warning no-breakpoint: Remove breakpoint(). [{warning.id}]"
            )
        }

    def test_only_blocking_diagnostics_reach_the_agent(self, stop, make_diagnostic):
        error = make_diagnostic(note=None)
        warning = make_diagnostic(warning=True, lines__start=2, lines__end=2)
        review = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout=json.dumps({"diagnostics": [error.as_json(), warning.as_json()]}),
            stderr="",
        )

        response = stop.review_response(review)

        assert response == {
            "decision": "block",
            "reason": (
                f"a.py:1: error no-print: Use logging, not print. [{error.id}]\n"
                f"{stop.REQUIRED_FIXES}"
            ),
            "systemMessage": (
                "codeguard warnings:\n"
                f"a.py:2: warning no-breakpoint: Remove breakpoint(). [{warning.id}]"
            ),
        }

    def test_finding_over_several_lines_shows_its_range(self, stop, make_diagnostic):
        finding = make_diagnostic(judged=True, lines__start=1, lines__end=2, message="Move it.")
        review = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout=json.dumps({"diagnostics": [finding.as_json()]}),
            stderr="",
        )

        response = stop.review_response(review)

        assert response == {
            "decision": "block",
            "reason": (
                f"a.py:1-2: error responsibility-placement: Move it. [{finding.id}]\n"
                f"{stop.REQUIRED_FIXES}"
            ),
        }

    def test_diagnostic_without_lines_shows_only_its_file(self, stop, make_diagnostic):
        judge_error = make_diagnostic(judge_error=True, severity=Severity.WARNING)
        review = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps({"diagnostics": [judge_error.as_json()]}),
            stderr="",
        )

        response = stop.review_response(review)

        assert response == {
            "systemMessage": (
                "codeguard warnings:\n"
                "a.py: warning responsibility-placement: The judge call failed, so this rule "
                f"was not checked. [{judge_error.id}]\n"
                "  claude exited with 1."
            )
        }

    def test_review_without_diagnostics_lets_the_agent_stop(self, stop):
        review = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps({"diagnostics": []}), stderr=""
        )

        assert stop.review_response(review) == {}

    def test_failed_review_goes_to_the_user_with_its_output(self, stop):
        review = subprocess.CompletedProcess(
            args=[], returncode=2, stdout="", stderr="Error: Cannot parse rule broken.yml\n"
        )

        response = stop.review_response(review)

        assert response == {
            "systemMessage": f"{stop.NOT_REVIEWED}\nError: Cannot parse rule broken.yml"
        }

    def test_output_that_is_not_a_review_goes_to_the_user(self, stop):
        review = subprocess.CompletedProcess(args=[], returncode=1, stdout="Traceback\n", stderr="")

        response = stop.review_response(review)

        assert response == {"systemMessage": f"{stop.NOT_REVIEWED}\nTraceback"}


class TestResponse:
    def test_missing_codeguard_goes_to_the_user(self, stop, tmp_path, monkeypatch):
        missing = tmp_path / "codeguard"
        monkeypatch.setenv("CODEGUARD", str(missing))

        response = stop.response("claude-code")

        error = f"[Errno 2] No such file or directory: '{missing}'"
        assert response == {"systemMessage": f"{stop.NOT_REVIEWED}\n{error}"}
