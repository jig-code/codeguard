from codeguard.config import ChangeKind


class TestFileClassification:
    def test_judged_lines_take_in_the_lines_of_the_triggers_kinds(self, make_file_classification):
        classified = make_file_classification(
            context_lines=frozenset({2, 3}),
            kind_lines={ChangeKind.CONTROL_FLOW: frozenset({1, 2, 3, 4})},
        )

        assert classified.judged_lines(frozenset({ChangeKind.CONTROL_FLOW})) == {1, 2, 3, 4}
        assert classified.judged_lines(frozenset({ChangeKind.CALL})) == {2, 3}
