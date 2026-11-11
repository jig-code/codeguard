from codeguard.syntax import Classification


class TestClassification:
    def test_judged_lines_take_in_the_lines_of_the_triggers_kinds(self):
        classification = Classification(
            judged={"a.py": frozenset({2, 3})},
            kind_lines={"a.py": {"control-flow": frozenset({1, 2, 3, 4})}},
        )

        assert classification.judged_lines("a.py", frozenset({"control-flow"})) == {1, 2, 3, 4}
        assert classification.judged_lines("a.py", frozenset({"call"})) == {2, 3}

    def test_file_it_holds_nothing_for_is_judged_whole(self):
        assert Classification().judged_lines("a.py") is None
