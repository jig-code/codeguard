"""codeguard's command line: what only the parser and the command functions can get wrong.

Each test names the wiring bug it catches; the behaviour behind it is tested in its unit's
suite. Most run `cli.run` in this process. Only the tests that need a second process start
one.
"""

import json
import subprocess
import sys
import sysconfig
import textwrap
from pathlib import Path

import pytest
import yaml
from claude_output import claude_stream, tool_use
from fake_cli import configure_fake_cli_response
from git_repo import GitRepo
from rules_package import write_package
from spans import finished_span_attributes

from codeguard import cli
from codeguard.file_lock import exclusive_lock
from codeguard.review import Severity

CODEGUARD = Path(sysconfig.get_path("scripts")) / "codeguard"
NO_PRINT_TEST = ".codeguard/rule-tests/no-print-test.yml"
NO_PRINT_SNAPSHOT = ".codeguard/rule-tests/__snapshots__/no-print-snapshot.yml"
TRACEBACK_HEADING = "Traceback (most recent call last):\n"
PASSING_NO_PRINT_TEST_REPORT = (
    "Running 1 tests\n"
    "\n"
    "----------- Case Details -----------\n"
    "PASS no-print  .\n"
    "\n"
    "test result: ok. 1 passed; 0 failed;\n"
)
INVOICE_BEFORE = textwrap.dedent("""\
    class Invoice:
        def total(self, order):
            return order.subtotal

        def label(self):
            return 'invoice'
""")
INVOICE_AFTER = textwrap.dedent("""\
    class Invoice:
        def total(self, order):
            return sum(line.price for line in order.lines)

        def label(self):
            return 'invoice'
""")


@pytest.fixture
def placement_binding() -> dict[str, object]:
    return {"rule": "placement", "paths": ["**/*.py"], "triggers": ["any"]}


@pytest.mark.usefixtures("cache_home")
class TestReviewCommand:
    def test_error_diagnostic_prints_and_exits_1(self, repo, make_diagnostic, monkeypatch, capfd):
        """Bug: review prints nothing, or exits 0 for a review that blocks."""
        repo.write("a.py", "print(1)\n")
        monkeypatch.chdir(repo.root)

        exit_code = cli.run(["review"])

        assert capfd.readouterr() == (f"{make_diagnostic()}\n", "")
        assert exit_code == 1

    def test_warning_diagnostic_prints_and_exits_0(self, repo, make_diagnostic, monkeypatch, capfd):
        """Bug: review exits 1 whatever the review found."""
        repo.write("a.py", "breakpoint()\n")
        monkeypatch.chdir(repo.root)

        exit_code = cli.run(["review"])

        assert capfd.readouterr() == (f"{make_diagnostic(warning=True)}\n", "")
        assert exit_code == 0

    def test_review_waits_for_a_running_review(self, repo, make_diagnostic):
        """Bug: two reviews of one repository run at once. Only two processes show it."""
        repo.write("a.py", "print(1)\n")

        with exclusive_lock(repo.root / ".git" / "codeguard-review.lock"):
            process = subprocess.Popen(
                [CODEGUARD, "review"], cwd=repo.root, stdout=subprocess.PIPE, text=True
            )
            with pytest.raises(subprocess.TimeoutExpired):
                process.wait(timeout=1)
        stdout, _ = process.communicate(timeout=30)

        assert stdout == f"{make_diagnostic()}\n"
        assert process.returncode == 1

    def test_base_reviews_committed_changes(self, repo, make_diagnostic, monkeypatch, capfd):
        """Bug: --base doesn't reach the line scope."""
        repo.git("switch", "--create", "feature")
        repo.write("a.py", "print(1)\n")
        repo.commit("Add a")
        monkeypatch.chdir(repo.root)

        exit_code = cli.run(["review", "--base", "main"])

        assert capfd.readouterr().out == f"{make_diagnostic()}\n"
        assert exit_code == 1

    def test_all_reviews_committed_unchanged_files(self, repo, make_diagnostic, monkeypatch, capfd):
        """Bug: --all doesn't reach the line scope."""
        repo.write("a.py", "print(1)\n")
        repo.commit("Add a")
        monkeypatch.chdir(repo.root)

        exit_code = cli.run(["review", "--all"])

        assert capfd.readouterr().out == f"{make_diagnostic()}\n"
        assert exit_code == 1

    def test_failed_command_prints_its_output_and_exits_2(self, repo, monkeypatch, capfd):
        """Bug: a command codeguard runs fails without its own error reaching the user."""
        repo.write(".codeguard/rules/pattern/broken.yml", "id: [\n")
        repo.write("a.py", "print(1)\n")
        monkeypatch.chdir(repo.root)

        exit_code = cli.run(["review"])

        out, err = capfd.readouterr()
        ast_grep_error, traceback = err.split(TRACEBACK_HEADING)
        assert out == ""
        assert ast_grep_error == (
            f"Error: Cannot parse rule {repo.root}/.codeguard/rules/pattern/broken.yml\n"
            "Help: The file is not a valid ast-grep rule. Please refer to doc and fix the error.\n"
            "See also: https://ast-grep.github.io/guide/rule-config.html\n"
            "\n"
            "✖ Caused by\n"
            "╰▻ Fail to parse yaml as RuleConfig\n"
            "╰▻ id: invalid type: sequence, expected a string at line 1 column 5\n"
            "\n"
        )
        assert traceback.endswith("returned non-zero exit status 8.\n")
        assert exit_code == 2

    @pytest.mark.parametrize(
        ("arguments", "expected_exit_code"), [([], 1), (["--skip-ci-only"], 0)]
    )
    def test_ci_only_rule_is_skipped_only_when_asked(
        self, repo, monkeypatch, arguments, expected_exit_code
    ):
        """Bug: --skip-ci-only doesn't reach the rulesets, or is always on."""
        write_package(repo, prefix="rules/")
        repo.write(
            ".codeguard/config.yaml",
            yaml.safe_dump(
                {
                    "packages": [
                        {
                            "kind": "path",
                            "path": "rules",
                            "rulesets": {
                                "python": {
                                    "exclude": ["responsibility-placement"],
                                    "rules": {"no-print": {"ci_only": True}},
                                }
                            },
                        }
                    ]
                }
            ),
        )
        (repo.root / ".codeguard/rules/pattern/no-print.yml").unlink()
        repo.write("a.py", "print(1)\n")
        monkeypatch.chdir(repo.root)

        exit_code = cli.run(["review", *arguments])

        assert exit_code == expected_exit_code


@pytest.mark.usefixtures("fake_cli_config", "cache_home")
class TestReviewDryRun:
    @pytest.mark.usefixtures("fake_claude_on_path")
    def test_lists_judge_calls_without_calling_claude(
        self, repo, make_judge_rule, placement_binding, monkeypatch, capfd
    ):
        """Bug: --dry-run calls the judge, or prints no plan."""
        repo.write(".codeguard/rules/judge/placement.md", make_judge_rule().text)
        repo.write(".codeguard/bindings/placement.yaml", yaml.safe_dump(placement_binding))
        repo.write(".codeguard/rules/judge/class-shape.md", make_judge_rule().text)
        repo.write(
            ".codeguard/bindings/class-shape.yaml",
            yaml.safe_dump(
                {"rule": "class-shape", "paths": ["**/*.py"], "triggers": ["class-header"]}
            ),
        )
        repo.write("a.py", "x = 1\n")
        repo.write("b.rb", "x = 1\n")
        configure_fake_cli_response({"exit_code": 1})
        monkeypatch.chdir(repo.root)

        exit_code = cli.run(["review", "--dry-run"])

        assert capfd.readouterr().out == (
            "Judge calls: 1 (0 cached, 1 new), 1 skipped by triggers\n"
            "\n"
            "By rule:\n"
            "     new  cached  skipped  rule\n"
            "       1       0        0  placement\n"
            "       0       0        1  class-shape\n"
            "\n"
            "By file:\n"
            "     new  cached  skipped  file\n"
            "       1       0        1  a.py\n"
            "\n"
            "Calls by file:\n"
            "a.py\n"
            "  new      placement\n"
            "  skipped  class-shape\n"
        )
        assert exit_code == 0

    def test_pattern_rule_error_is_printed_and_exits_1(
        self, repo, make_diagnostic, monkeypatch, capfd
    ):
        """Bug: --dry-run drops the pattern rules' result or its exit code."""
        repo.write("a.py", "print(1)\n")
        monkeypatch.chdir(repo.root)

        exit_code = cli.run(["review", "--dry-run"])

        assert capfd.readouterr() == (
            f"{make_diagnostic()}\nJudge calls: 0 (0 cached, 0 new), 0 skipped by triggers\n",
            "",
        )
        assert exit_code == 1

    def test_dry_run_has_no_json_format(self, repo, monkeypatch, capfd):
        """Bug: the parser accepts --dry-run with --format json, which --dry-run ignores."""
        monkeypatch.chdir(repo.root)

        with pytest.raises(SystemExit) as exit_:
            cli.run(["review", "--dry-run", "--format", "json"])

        assert capfd.readouterr().err.endswith(
            "error: argument --format: not allowed with argument --dry-run\n"
        )
        assert exit_.value.code == 2


@pytest.mark.usefixtures("cache_home")
class TestReviewJsonFormat:
    def test_prints_one_object_with_the_diagnostics(
        self, repo, make_diagnostic, monkeypatch, capfd
    ):
        """Bug: --format json doesn't reach the writer."""
        repo.write("a.py", "print(1)\n")
        monkeypatch.chdir(repo.root)

        exit_code = cli.run(["review", "--format", "json"])

        assert json.loads(capfd.readouterr().out) == {"diagnostics": [make_diagnostic().as_json()]}
        assert exit_code == 1


@pytest.mark.usefixtures("fake_cli_config", "fake_claude_on_path", "cache_home")
class TestReviewJudgeErrorsAsWarnings:
    def test_judge_error_is_a_warning_with_the_flag(  # noqa: PLR0913 - pytest fixtures
        self, repo, make_judge_rule, placement_binding, make_diagnostic, monkeypatch, capfd
    ):
        """Bug: --judge-errors-as-warnings doesn't reach the review's result."""
        repo.write(".codeguard/rules/judge/placement.md", make_judge_rule().text)
        repo.write(".codeguard/bindings/placement.yaml", yaml.safe_dump(placement_binding))
        repo.commit("Bind the rule")
        repo.write("a.py", "x = 1\n")
        configure_fake_cli_response({"stdout": "rate limited\n", "exit_code": 1})
        monkeypatch.chdir(repo.root)

        exit_code = cli.run(["review", "--judge-errors-as-warnings"])

        judge_error = make_diagnostic(
            judge_error=True,
            rule="placement",
            severity=Severity.WARNING,
            note="claude exited with 1.\nstdout:\nrate limited\n\nstderr:\n",
        )
        assert capfd.readouterr().out == f"{judge_error}\n"
        assert exit_code == 0


@pytest.mark.usefixtures("fake_cli_config", "fake_claude_on_path", "cache_home")
class TestReviewJudgeCache:
    def test_cached_verdict_is_reused_until_a_file_the_judge_read_changes(
        self, repo, make_judge_rule, placement_binding, monkeypatch, tmp_path
    ):
        """Bug: review judges without the cache, or with one that doesn't outlast a run."""
        repo.write(".codeguard/rules/judge/placement.md", make_judge_rule().text)
        repo.write(".codeguard/bindings/placement.yaml", yaml.safe_dump(placement_binding))
        repo.commit("Bind the rule")
        repo.write("a.py", "x = 1\n")
        repo.write("orders/pricing.toml", "discount = 5\n")
        calls = tmp_path / "calls"
        configure_fake_cli_response(
            {
                "stdout": claude_stream(
                    [], messages=(tool_use("Read", file_path="orders/pricing.toml"),)
                ),
                "calls": str(calls),
            }
        )
        monkeypatch.chdir(repo.root)
        cli.run(["review"])
        cli.run(["review"])
        repo.write("orders/pricing.toml", "discount = 10\n")

        cli.run(["review"])

        assert calls.read_text() == "called\ncalled\n"


@pytest.mark.usefixtures("cache_home")
class TestConfigCommand:
    def test_prints_the_configured_setting(self, repo, monkeypatch, capfd):
        """Bug: config prints another setting, or the default over the configured one."""
        repo.write(".codeguard/config.yaml", yaml.safe_dump({"review_time_limit_minutes": 10}))
        monkeypatch.chdir(repo.root)

        exit_code = cli.run(["config", "review_time_limit_minutes"])

        assert capfd.readouterr().out == "10\n"
        assert exit_code == 0

    def test_creates_no_command_span(self, repo, monkeypatch, capfire):
        """Bug: each CI review leaves a separate trace for the config call that sets it up."""
        monkeypatch.chdir(repo.root)

        cli.run(["config", "review_time_limit_minutes"])
        cli.run(["review", "--dry-run"])

        assert finished_span_attributes(capfire, "codeguard {command}") == [{"command": "review"}]


@pytest.fixture
def invoice_package(tmp_path_factory: pytest.TempPathFactory) -> GitRepo:
    package = GitRepo.init(tmp_path_factory.mktemp("package").resolve())
    write_package(package)
    case = {
        "name": "totals the order lines",
        "inputs": {"file": "invoice.py", "before": INVOICE_BEFORE, "after": INVOICE_AFTER},
        "expected_output": {"outcome": "invalid"},
    }
    package.write(
        "python/rule-evals/responsibility-placement.yaml", yaml.safe_dump({"cases": [case]})
    )
    return package


@pytest.mark.usefixtures("fake_cli_config", "fake_claude_on_path", "cache_home")
class TestEvalCommand:
    def test_other_commands_do_not_load_pydantic_evals(self):
        """Bug: importing the CLI loads pydantic-evals. Only a fresh interpreter shows it."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys, codeguard.cli; print('pydantic_evals' in sys.modules)",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        assert result.stdout == "False\n"

    @pytest.mark.parametrize("from_package", [True, False], ids=["in-package", "package-path"])
    def test_invalid_case_judged_valid_is_reported_and_exits_1(
        self, invoice_package, tmp_path, monkeypatch, capfd, from_package
    ):
        """Bug: eval ignores its package argument, or exits 0 for a failed eval."""
        configure_fake_cli_response({"stdout": claude_stream([])})
        monkeypatch.chdir(invoice_package.root if from_package else tmp_path)

        exit_code = cli.run(["eval"] if from_package else ["eval", str(invoice_package.root)])

        out = capfd.readouterr().out
        assert "Evaluation Summary: responsibility-placement on claude-cli's default model" in out
        assert out.endswith(
            "responsibility-placement totals the order lines: expected outcome "
            "invalid, got outcome valid\n  reason: Judged.\n"
        )
        assert exit_code == 1

    def test_judges_only_the_selected_rule_and_case(
        self, invoice_package, make_judge_rule, monkeypatch, tmp_path
    ):
        """Bug: --rule or --case doesn't reach the selection."""
        invoice_package.write("python/rules/judge/naming.md", make_judge_rule().text)
        invoice_package.write(
            "python/bindings/naming.yaml",
            yaml.safe_dump({"rule": "naming", "paths": ["**/*.py"], "triggers": ["any"]}),
        )
        invoice_package.write(
            "python/rule-evals/naming.yaml",
            yaml.safe_dump(
                {
                    "cases": [
                        {
                            "name": "names the order lines",
                            "inputs": {"file": "invoice.py", "after": INVOICE_AFTER},
                            "expected_output": {"outcome": "valid"},
                        },
                        {
                            "name": "names the invoice",
                            "inputs": {"file": "invoice.py", "after": INVOICE_BEFORE},
                            "expected_output": {"outcome": "valid"},
                        },
                    ]
                }
            ),
        )
        calls = tmp_path / "calls"
        configure_fake_cli_response({"stdout": claude_stream([]), "calls": str(calls)})
        monkeypatch.chdir(invoice_package.root)

        cli.run(["eval", "--rule", "naming", "--case", "order lines"])

        assert calls.read_text() == "called\n"

    @pytest.mark.parametrize(
        ("options", "model"),
        [
            (["--provider", "claude-cli"], None),
            (["--provider", "claude-cli", "--model", "claude-haiku-5-5"], "claude-haiku-5-5"),
        ],
        ids=["default-model", "given-model"],
    )
    def test_judges_with_the_given_provider_and_model(
        self, invoice_package, tmp_path, monkeypatch, options, model
    ):
        """Bug: --provider or --model doesn't reach the override, or the default is wrong."""
        invoice_package.write(
            "python/bindings/responsibility-placement.yaml",
            yaml.safe_dump(
                {
                    "rule": "responsibility-placement",
                    "paths": ["**/*.py"],
                    "triggers": ["any"],
                    "provider": "gemini",
                    "model": "gemini-4-argon",
                }
            ),
        )
        record = tmp_path / "request.json"
        configure_fake_cli_response({"stdout": claude_stream([]), "record": str(record)})
        monkeypatch.chdir(invoice_package.root)

        cli.run(["eval", *options])

        arguments = json.loads(record.read_text())["arguments"]
        assert dict(zip(arguments, arguments[1:], strict=False)).get("--model") == model

    def test_model_without_a_provider_exits_2(self, tmp_path, monkeypatch, capfd):
        """Bug: --model without --provider is accepted and silently ignored."""
        monkeypatch.chdir(tmp_path)

        with pytest.raises(SystemExit) as exit_:
            cli.run(["eval", "--model", "claude-haiku-5-5"])

        assert capfd.readouterr().err.endswith("error: --model needs --provider\n")
        assert exit_.value.code == 2

    def test_eval_and_review_send_claude_the_same_request(
        self, invoice_package, tmp_path_factory, tmp_path, monkeypatch
    ):
        """Bug: eval and review build the judge's request differently."""
        project = GitRepo.init(tmp_path_factory.mktemp("project").resolve())
        project.write(
            ".codeguard/config.yaml",
            yaml.safe_dump(
                {
                    "packages": [
                        {
                            "kind": "path",
                            "path": str(invoice_package.root),
                            "rulesets": {"python": {"include": ["responsibility-placement"]}},
                        }
                    ]
                }
            ),
        )
        project.write("invoice.py", INVOICE_BEFORE)
        project.commit("Add the invoice")
        project.write("invoice.py", INVOICE_AFTER)
        eval_record = tmp_path / "eval.json"
        review_record = tmp_path / "review.json"
        configure_fake_cli_response({"stdout": claude_stream([]), "record": str(eval_record)})
        monkeypatch.chdir(invoice_package.root)
        cli.run(["eval"])
        configure_fake_cli_response({"stdout": claude_stream([]), "record": str(review_record)})
        monkeypatch.chdir(project.root)

        cli.run(["review"])

        eval_request = json.loads(eval_record.read_text())
        review_request = json.loads(review_record.read_text())
        assert eval_request["arguments"] == review_request["arguments"]
        assert eval_request["prompt"] == review_request["prompt"]


class TestTestCommand:
    def test_passing_rule_tests_exit_0(self, repo, monkeypatch, capfd):
        """Bug: test prints no report, or exits 1 for tests that pass."""
        repo.write(NO_PRINT_TEST, yaml.safe_dump({"id": "no-print", "valid": ["logging.info(1)"]}))
        monkeypatch.chdir(repo.root)

        exit_code = cli.run(["test"])

        assert capfd.readouterr() == (PASSING_NO_PRINT_TEST_REPORT, "")
        assert exit_code == 0

    def test_failing_rule_tests_exit_1(self, repo, monkeypatch, capfd):
        """Bug: test exits 0 for tests that fail."""
        repo.write(NO_PRINT_TEST, yaml.safe_dump({"id": "no-print", "valid": ["print(1)"]}))
        monkeypatch.chdir(repo.root)

        exit_code = cli.run(["test"])

        assert capfd.readouterr() == (
            "Running 1 tests\n"
            "\n"
            "----------- Case Details -----------\n"
            "[Noisy] Expect no-print to report no issue, but some issues found in:\n"
            "\n"
            "  print(1)\n"
            "\n"
            "FAIL no-print  N\n"
            "\n",
            "Error: test failed. 0 passed; 1 failed;\n"
            "Help: You can use ast-grep playground to debug your rules and test cases.\n"
            "See also: https://ast-grep.github.io/playground.html\n"
            "\n",
        )
        assert exit_code == 1

    def test_config_error_prints_its_traceback_and_exits_2(self, tmp_path, monkeypatch, capfd):
        """Bug: an error codeguard raises leaves the user no traceback, or exits 1."""
        package = GitRepo.init(tmp_path.resolve())
        write_package(package)
        package.write(
            "python/rule-tests/triggers/no-print-test.yml", yaml.safe_dump({"id": "no-print"})
        )
        monkeypatch.chdir(package.root)

        exit_code = cli.run(["test"])

        _, traceback = capfd.readouterr().err.split(TRACEBACK_HEADING)
        assert traceback.splitlines()[-2:] == [
            f"codeguard.config.config_error.ConfigError: {package.root}/python is invalid:",
            "  unexpected rule-tests/triggers",
        ]
        assert exit_code == 2

    def test_package_repo_runs_each_ruleset_tests(self, tmp_path, monkeypatch, capfd):
        """Bug: test in a package repository runs only its local ruleset's validations."""
        package = GitRepo.init(tmp_path.resolve())
        write_package(package)
        package.write(
            "python/rule-tests/no-print-test.yml",
            yaml.safe_dump({"id": "no-print", "valid": ["logging.info(1)"]}),
        )
        monkeypatch.chdir(package.root)

        exit_code = cli.run(["test"])

        assert capfd.readouterr().out == PASSING_NO_PRINT_TEST_REPORT + (
            "warning: responsibility-placement: broad triggers any; "
            "a gate on the code its violations need skips more files\n"
        )
        assert exit_code == 0

    def test_update_all_writes_the_snapshots(self, repo, monkeypatch):
        """Bug: --update-all doesn't reach the snapshot validations."""
        repo.write(NO_PRINT_TEST, yaml.safe_dump({"id": "no-print", "invalid": ["print(1)"]}))
        monkeypatch.chdir(repo.root)

        exit_code = cli.run(["test", "--update-all"])

        assert (repo.root / NO_PRINT_SNAPSHOT).is_file()
        assert exit_code == 0

    def test_missing_why_fail_fails_the_run(self, repo, monkeypatch, capfd):
        """Bug: --missing-why doesn't reach the why validation."""
        repo.write(
            ".codeguard/rules/pattern/no-print.yml",
            yaml.safe_dump(
                {
                    "id": "no-print",
                    "language": "python",
                    "severity": "error",
                    "message": "Use logging, not print.",
                    "rule": {"pattern": "print($$$ARGS)"},
                }
            ),
        )
        repo.write(NO_PRINT_TEST, yaml.safe_dump({"id": "no-print", "valid": ["logging.info(1)"]}))
        monkeypatch.chdir(repo.root)

        exit_code = cli.run(["test", "--missing-why", "fail"])

        assert (
            capfd.readouterr().out == PASSING_NO_PRINT_TEST_REPORT + "no-print: no metadata.why\n"
        )
        assert exit_code == 1
