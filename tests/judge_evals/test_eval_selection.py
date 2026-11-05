from codeguard.judge_evals import EvalSelection

CASE_NAMES = {
    "enum-usage": ("flags a string", "allows the member"),
    "placement": ("allows an assigned count",),
}


class TestEvalSelection:
    def test_selects_every_rule_and_case_by_default(self):
        selection = EvalSelection()

        assert selection.selects_rule("enum-usage")
        assert selection.selects_case("flags a string")
        assert selection.problems(CASE_NAMES) == ()

    def test_selects_only_the_named_rules(self):
        selection = EvalSelection(rules=frozenset({"placement"}))

        assert (selection.selects_rule("placement"), selection.selects_rule("enum-usage")) == (
            True,
            False,
        )

    def test_selects_a_case_whose_name_contains_any_of_the_texts(self):
        selection = EvalSelection(cases=("member", "count"))

        assert all(
            selection.selects_case(name)
            for name in ("allows the member", "allows an assigned count")
        )
        assert not selection.selects_case("flags a string")

    def test_rule_matching_no_judge_rule_is_a_problem(self):
        selection = EvalSelection(rules=frozenset({"placement", "enum-usge"}))

        assert selection.problems(CASE_NAMES) == ("--rule enum-usge: no judge rule enum-usge",)

    def test_case_text_matching_no_case_of_the_selected_rules_is_a_problem(self):
        selection = EvalSelection(rules=frozenset({"placement"}), cases=("member", "count"))

        assert selection.problems(CASE_NAMES) == (
            "--case member: no case of the selected rules has it in its name",
        )
