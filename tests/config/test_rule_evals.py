import pytest
import yaml
from pydantic import ValidationError

from codeguard.config import ConfigError, FileEdit, RuleEval, RuleEvalReader


class TestRuleEvals:
    def test_eval_is_named_after_its_file(self, tmp_path, make_rule_eval_case):
        case = make_rule_eval_case()
        (tmp_path / "rule-evals").mkdir()
        (tmp_path / "rule-evals/enum-usage.yaml").write_text(
            yaml.safe_dump({"cases": [case.model_dump(mode="json", exclude_defaults=True)]})
        )

        evals = RuleEvalReader(tmp_path).read()

        assert evals == [
            (tmp_path / "rule-evals/enum-usage.yaml", RuleEval(name="enum-usage", cases=(case,)))
        ]

    def test_eval_file_violation_gives_its_lines_as_a_range(
        self, tmp_path, make_edit_verdict, make_judged_violation
    ):
        (tmp_path / "rule-evals").mkdir()
        (tmp_path / "rule-evals/enum-usage.yaml").write_text(
            "cases:\n"
            "  - name: a string\n"
            "    inputs:\n"
            "      file: module.py\n"
            "      after: |\n"
            "        ship(status='shipped')\n"
            "    expected_output:\n"
            "      outcome: invalid\n"
            "      violations:\n"
            "        - lines: {start: 1, end: 2}\n"
            "          confidence: 0.9\n"
            "          message: Pass the member.\n"
        )

        [(_, rule_eval)] = RuleEvalReader(tmp_path).read()

        assert rule_eval.cases[0].expected_output == make_edit_verdict(
            violations=(make_judged_violation(lines__start=1, lines__end=2),)
        )

    def test_eval_file_ending_in_yml_is_loaded(self, tmp_path, make_rule_eval_case):
        case = make_rule_eval_case()
        (tmp_path / "rule-evals").mkdir()
        (tmp_path / "rule-evals/enum-usage.yml").write_text(
            yaml.safe_dump({"cases": [case.model_dump(mode="json", exclude_defaults=True)]})
        )

        evals = RuleEvalReader(tmp_path).read()

        assert evals == [
            (tmp_path / "rule-evals/enum-usage.yml", RuleEval(name="enum-usage", cases=(case,)))
        ]

    def test_two_eval_files_naming_one_rule_raise_a_config_error(
        self, tmp_path, make_rule_eval_case
    ):
        case = make_rule_eval_case().model_dump(mode="json", exclude_defaults=True)
        (tmp_path / "rule-evals").mkdir()
        (tmp_path / "rule-evals/enum-usage.yaml").write_text(yaml.safe_dump({"cases": [case]}))
        (tmp_path / "rule-evals/more.yaml").write_text(
            yaml.safe_dump({"name": "enum-usage", "cases": [case]})
        )

        with pytest.raises(ConfigError) as error:
            RuleEvalReader(tmp_path).read()

        assert str(error.value) == (
            "a rule has one eval file; remove one of:\n"
            f"  {tmp_path}/rule-evals/enum-usage.yaml\n"
            f"  {tmp_path}/rule-evals/more.yaml"
        )

    def test_yaml_and_yml_eval_files_for_one_rule_raise_a_config_error(
        self, tmp_path, make_rule_eval_case
    ):
        case = make_rule_eval_case().model_dump(mode="json", exclude_defaults=True)
        (tmp_path / "rule-evals").mkdir()
        (tmp_path / "rule-evals/enum-usage.yaml").write_text(yaml.safe_dump({"cases": [case]}))
        (tmp_path / "rule-evals/enum-usage.yml").write_text(yaml.safe_dump({"cases": [case]}))

        with pytest.raises(ConfigError) as error:
            RuleEvalReader(tmp_path).read()

        assert str(error.value) == (
            "a rule has one eval file; remove one of:\n"
            f"  {tmp_path}/rule-evals/enum-usage.yaml\n"
            f"  {tmp_path}/rule-evals/enum-usage.yml"
        )

    def test_codeguard_0_4_eval_file_raises_asking_to_convert_it(self, tmp_path):
        (tmp_path / "rule-evals").mkdir()
        (tmp_path / "rule-evals/enum-usage-eval.yml").write_text(
            yaml.safe_dump({"id": "enum-usage", "invalid": [{"after": "ship(status='shipped')\n"}]})
        )

        with pytest.raises(ConfigError) as error:
            RuleEvalReader(tmp_path).read()

        assert str(error.value) == (
            f"{tmp_path}/rule-evals/enum-usage-eval.yml is a codeguard 0.4 rule eval; "
            "convert it to rule-evals/<rule id>.yaml"
        )

    @pytest.mark.parametrize(
        ("content", "error"),
        [
            pytest.param(
                {"cases": [{"name": "a string", "inputs": {"after": "x"}}]},
                "cases.0.expected_output: Field required",
                id="case-without-expected-output",
            ),
            pytest.param(
                {"cases": [{"inputs": {"after": "x"}, "expected_output": {"outcome": "valid"}}]},
                "cases.0.name: Field required",
                id="case-without-a-name",
            ),
            pytest.param(
                {
                    "cases": [
                        {
                            "name": "a string",
                            "inputs": {"after": "x"},
                            "expected_output": {"outcome": "valid"},
                        },
                        {
                            "name": "a string",
                            "inputs": {"after": "y"},
                            "expected_output": {"outcome": "valid"},
                        },
                    ]
                },
                "cases: Value error, cases share a name: a string",
                id="cases-sharing-a-name",
            ),
            pytest.param(
                {
                    "cases": [
                        {
                            "name": "a string",
                            "inputs": {"after": "x"},
                            "expected_output": {"outcome": "valid"},
                        }
                    ],
                    "evaluators": ["EqualsExpected"],
                },
                "evaluators: Extra inputs are not permitted",
                id="eval-declaring-evaluators",
            ),
            pytest.param(
                {
                    "cases": [
                        {
                            "name": "a string",
                            "inputs": {"after": "x"},
                            "expected_output": {"outcome": "uncertain"},
                        }
                    ]
                },
                "cases.0.expected_output: Value error, a case expects invalid, valid or "
                "skipped; one the judge can't decide isn't clear enough for a rule eval",
                id="case-expecting-uncertain",
            ),
            pytest.param(
                {
                    "cases": [
                        {
                            "name": "a string",
                            "inputs": {"after": "x"},
                            "expected_output": {"outcome": "invalid", "reason": "A string."},
                        }
                    ]
                },
                "cases.0.expected_output: Value error, a case expects no reason: the judge's "
                "reason is printed with the eval for whoever reads it, never checked",
                id="case-expecting-a-reason",
            ),
        ],
    )
    def test_malformed_eval_file_raises_a_config_error_naming_the_field(
        self, tmp_path, content, error
    ):
        (tmp_path / "rule-evals").mkdir()
        (tmp_path / "rule-evals/enum-usage.yaml").write_text(yaml.safe_dump(content))

        with pytest.raises(ConfigError) as raised:
            RuleEvalReader(tmp_path).read()

        assert str(raised.value) == f"{tmp_path}/rule-evals/enum-usage.yaml is invalid:\n  {error}"


class TestEditVerdict:
    def test_listing_gives_a_violation_on_one_line_its_line(
        self, make_edit_verdict, make_judged_violation
    ):
        review = make_edit_verdict(
            reason="Judged.", violations=(make_judged_violation(lines__start=2, lines__end=2),)
        )

        assert review.listing == "\n  reason: Judged.\n  line 2 (0.90): Pass the member."

    def test_listing_gives_a_violation_over_several_lines_its_first_and_last_line(
        self, make_edit_verdict, make_judged_violation
    ):
        review = make_edit_verdict(
            reason="Judged.", violations=(make_judged_violation(lines__start=2, lines__end=4),)
        )

        assert review.listing == "\n  reason: Judged.\n  lines 2-4 (0.90): Pass the member."


class TestFileEdit:
    @staticmethod
    def problems(error: pytest.ExceptionInfo[ValidationError]) -> list[str]:
        return [problem["msg"] for problem in error.value.errors()]

    def test_unchanged_files_may_not_list_the_edited_file(self):
        with pytest.raises(ValidationError) as error:
            FileEdit(after="label = status.value", unchanged={"module.py": "label = status.name"})

        assert self.problems(error) == ["Value error, unchanged lists the edited file module.py"]

    @pytest.mark.parametrize("path", ["/etc/module.py", "../module.py", "./module.py", "."])
    def test_unchanged_path_must_be_a_normalized_path_inside_the_repository(self, path):
        with pytest.raises(ValidationError) as error:
            FileEdit(after="label = status.value", unchanged={path: "label = status.name"})

        assert self.problems(error) == [f"Value error, {path} is not a normalized relative path"]

    def test_edited_file_must_be_inside_the_repository(self):
        with pytest.raises(ValidationError) as error:
            FileEdit(file="../module.py", after="label = status.value")

        assert self.problems(error) == [
            "Value error, ../module.py is not a normalized relative path"
        ]

    def test_unchanged_path_may_not_be_inside_git(self):
        with pytest.raises(ValidationError) as error:
            FileEdit(after="label = status.value", unchanged={".git/config": "[core]"})

        assert self.problems(error) == ["Value error, .git/config is inside .git"]

    def test_before_files_leave_out_the_edited_file_a_new_file_lacks(self, make_file_edit):
        edit = make_file_edit(file="module.py", before=None, unchanged={"util.py": "a = 1\n"})

        assert edit.before_files() == {"util.py": "a = 1\n"}

    def test_before_and_after_files_hold_each_text_under_the_prefix(self, make_file_edit):
        edit = make_file_edit(
            file="module.py",
            before="count = 1\n",
            after="count = 2\n",
            unchanged={"util.py": "a = 1\n"},
        )

        assert edit.before_files("rule/1/") == {
            "rule/1/util.py": "a = 1\n",
            "rule/1/module.py": "count = 1\n",
        }
        assert edit.after_files("rule/1/") == {
            "rule/1/util.py": "a = 1\n",
            "rule/1/module.py": "count = 2\n",
        }


class TestRuleEvalByLanguage:
    def test_rule_naming_several_languages_is_split_into_one_eval_per_language(
        self, make_rule_eval_case
    ):
        python = make_rule_eval_case(name="a status literal", inputs__file="orders.py")
        typescript = make_rule_eval_case(
            name="a status literal in a script", inputs__file="orders.ts"
        )
        rule_eval = RuleEval(name="knowledge-stated-once", cases=(python, typescript))

        split = rule_eval.by_language(frozenset({"python", "typescript"}))

        assert split == (
            ("python", RuleEval(name="knowledge-stated-once (python)", cases=(python,))),
            (
                "typescript",
                RuleEval(name="knowledge-stated-once (typescript)", cases=(typescript,)),
            ),
        )

    def test_rule_naming_one_language_keeps_one_eval(self, make_rule_eval_case):
        python = make_rule_eval_case(name="a status literal", inputs__file="orders.py")
        rule_eval = RuleEval(name="knowledge-stated-once", cases=(python,))

        split = rule_eval.by_language(frozenset({"python"}))

        assert split == (("python", rule_eval),)
