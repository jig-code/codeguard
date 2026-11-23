import importlib.util
import json
import subprocess
from pathlib import Path

from codeguard.review import Severity

STOP_SCRIPT = Path(__file__).resolve().parents[3] / "plugin" / "hooks" / "stop.py"
_SPEC = importlib.util.spec_from_file_location("stop", STOP_SCRIPT)
assert _SPEC is not None
assert _SPEC.loader is not None
stop = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(stop)


class TestReviewResponse:
    def test_blocking_diagnostic_goes_to_the_agent_as_a_required_fix(self, make_diagnostic):
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
            "reason": f"{diagnostic}\n{stop.REQUIRED_FIXES}",
        }

    def test_warning_goes_to_the_user(self, make_diagnostic):
        warning = make_diagnostic(warning=True)
        review = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps({"diagnostics": [warning.as_json()]}),
            stderr="",
        )

        response = stop.review_response(review)

        assert response == {"systemMessage": f"codeguard warnings:\n{warning}"}

    def test_only_blocking_diagnostics_reach_the_agent(self, make_diagnostic):
        error = make_diagnostic()
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
            "reason": f"{error}\n{stop.REQUIRED_FIXES}",
            "systemMessage": f"codeguard warnings:\n{warning}",
        }

    def test_judged_finding_over_several_lines_shows_its_range(self, make_diagnostic):
        finding = make_diagnostic(judged=True, lines__start=1, lines__end=2, message="Move it.")
        review = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout=json.dumps({"diagnostics": [finding.as_json()]}),
            stderr="",
        )

        response = stop.review_response(review)

        assert response == {"decision": "block", "reason": f"{finding}\n{stop.REQUIRED_FIXES}"}

    def test_judge_error_without_lines_shows_its_file(self, make_diagnostic):
        judge_error = make_diagnostic(judge_error=True, severity=Severity.WARNING)
        review = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps({"diagnostics": [judge_error.as_json()]}),
            stderr="",
        )

        response = stop.review_response(review)

        assert response == {"systemMessage": f"codeguard warnings:\n{judge_error}"}

    def test_review_without_diagnostics_lets_the_agent_stop(self):
        review = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps({"diagnostics": []}), stderr=""
        )

        assert stop.review_response(review) == {}

    def test_failed_review_goes_to_the_user_with_its_output(self):
        review = subprocess.CompletedProcess(
            args=[], returncode=2, stdout="", stderr="Error: Cannot parse rule broken.yml\n"
        )

        response = stop.review_response(review)

        assert response == {
            "systemMessage": f"{stop.NOT_REVIEWED}\nError: Cannot parse rule broken.yml"
        }

    def test_output_that_is_not_a_review_goes_to_the_user(self):
        review = subprocess.CompletedProcess(args=[], returncode=1, stdout="Traceback\n", stderr="")

        response = stop.review_response(review)

        assert response == {"systemMessage": f"{stop.NOT_REVIEWED}\nTraceback"}


class TestResponse:
    def test_missing_codeguard_goes_to_the_user(self, tmp_path, monkeypatch):
        missing = tmp_path / "codeguard"
        monkeypatch.setenv("CODEGUARD", str(missing))

        response = stop.response("claude-code")

        error = f"[Errno 2] No such file or directory: '{missing}'"
        assert response == {"systemMessage": f"{stop.NOT_REVIEWED}\n{error}"}
