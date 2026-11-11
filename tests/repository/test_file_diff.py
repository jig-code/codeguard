from codeguard.repository import FileDiff, Removal
from codeguard.repository.file_diff import AddedRow, KeptRow, RemovedRow


class TestFileDiffFromRows:
    def test_added_blank_lines_are_not_added_lines(self):
        rows = [
            KeptRow(1, 1),
            KeptRow(2, 2),
            AddedRow(3, b""),
            AddedRow(4, b"    def y(self):"),
            AddedRow(5, b"        pass"),
        ]

        diff = FileDiff.from_rows("a.py", rows)

        assert diff == FileDiff(
            base_path="a.py",
            added_lines=frozenset({4, 5}),
            head_lines_by_base_line={1: 1, 2: 2},
        )

    def test_code_replaced_by_blank_lines_is_a_deletion_point_after_the_line_before_it(self):
        rows = [KeptRow(1, 1), RemovedRow(2, b"b = 1"), AddedRow(2, b""), KeptRow(3, 3)]

        diff = FileDiff.from_rows("a.py", rows)

        assert diff == FileDiff(
            base_path="a.py",
            deletion_points=frozenset({1}),
            removals=(Removal(shown_before=2, reported_line=1, rows=(b"b = 1",), base_lines=(2,)),),
            head_lines_by_base_line={1: 1, 3: 3},
            removed_base_lines=frozenset({2}),
        )

    def test_removed_blank_lines_are_not_a_deletion_point(self):
        rows = [KeptRow(1, 1), KeptRow(2, 2), RemovedRow(3, b""), KeptRow(4, 3)]

        diff = FileDiff.from_rows("a.py", rows)

        assert diff == FileDiff(
            base_path="a.py",
            head_lines_by_base_line={1: 1, 2: 2, 4: 3},
            removed_base_lines=frozenset({3}),
        )

    def test_code_replaced_by_a_blank_first_line_is_a_deletion_point_on_line_1(self):
        rows = [RemovedRow(1, b"import os"), AddedRow(1, b""), KeptRow(2, 2)]

        diff = FileDiff.from_rows("a.py", rows)

        assert diff == FileDiff(
            base_path="a.py",
            deletion_points=frozenset({1}),
            removals=(
                Removal(shown_before=1, reported_line=1, rows=(b"import os",), base_lines=(1,)),
            ),
            head_lines_by_base_line={2: 2},
            removed_base_lines=frozenset({1}),
        )

    def test_removed_lines_are_a_deletion_point_after_the_line_before_them(self):
        rows = [KeptRow(1, 1), RemovedRow(2, b"b = 1"), KeptRow(3, 2)]

        diff = FileDiff.from_rows("a.py", rows)

        assert diff == FileDiff(
            base_path="a.py",
            deletion_points=frozenset({1}),
            removals=(Removal(shown_before=2, reported_line=1, rows=(b"b = 1",), base_lines=(2,)),),
            head_lines_by_base_line={1: 1, 3: 2},
            removed_base_lines=frozenset({2}),
        )


class TestFileDiffOfNewFile:
    def test_new_file_ending_in_a_newline_adds_its_lines_with_code(self):
        assert FileDiff.of_new_file(b"a = 1\n\nb = 1\n") == FileDiff(added_lines=frozenset({1, 3}))

    def test_new_file_without_a_final_newline_adds_its_last_line(self):
        assert FileDiff.of_new_file(b"a = 1\nb = 1") == FileDiff(added_lines=frozenset({1, 2}))

    def test_new_file_of_only_blank_lines_adds_no_lines(self):
        assert FileDiff.of_new_file(b"\n  \n") == FileDiff()
