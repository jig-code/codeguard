from git_repo import GitRepo

from codeguard.repository import AllLines, ChangedLines, FileDiff, LineScopes, Removal, WorkingTree
from codeguard.repository.file_diff import KeptRow, RemovedRow


class TestLineScopes:
    def test_changed_files_from_head_are_uncommitted_and_untracked_files(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("unstaged.py", "a = 1\n")
        git_repo.write("staged.py", "b = 1\n")
        git_repo.write("deleted.py", "c = 1\n")
        git_repo.commit("Add modules")
        git_repo.write("unstaged.py", "a = 2\n")
        git_repo.write("staged.py", "b = 2\n")
        git_repo.git("add", "staged.py")
        (git_repo.root / "deleted.py").unlink()
        git_repo.write("untracked.py", "d = 1\n")

        changed = LineScopes(WorkingTree.at(git_repo.root)).changed_lines("HEAD")

        assert changed == ChangedLines(
            {
                "staged.py": FileDiff(
                    base_path="staged.py",
                    added_lines=frozenset({1}),
                    deletion_points=frozenset(),
                    removals=(
                        Removal(
                            shown_before=1, reported_line=1, rows=(RemovedRow(1, text=b"b = 1"),)
                        ),
                    ),
                    head_lines_by_base_line={},
                    removed_base_lines=frozenset({1}),
                ),
                "unstaged.py": FileDiff(
                    base_path="unstaged.py",
                    added_lines=frozenset({1}),
                    deletion_points=frozenset(),
                    removals=(
                        Removal(
                            shown_before=1, reported_line=1, rows=(RemovedRow(1, text=b"a = 1"),)
                        ),
                    ),
                    head_lines_by_base_line={},
                    removed_base_lines=frozenset({1}),
                ),
                "untracked.py": FileDiff(
                    base_path=None,
                    added_lines=frozenset({1}),
                    deletion_points=frozenset(),
                    removals=(),
                    head_lines_by_base_line={},
                    removed_base_lines=frozenset(),
                ),
            },
            base=git_repo.head(),
        )

    def test_changes_since_the_merge_base_leave_out_the_base_branch_and_have_no_base_path(
        self, tmp_path
    ):
        git_repo = GitRepo.init(tmp_path.resolve())
        merge_base = git_repo.head()
        git_repo.git("switch", "--create", "feature")
        git_repo.write("committed.py", "a = 1\n")
        git_repo.commit("Add committed")
        git_repo.git("switch", "main")
        git_repo.write("main_only.py", "b = 1\n")
        git_repo.commit("Add main_only")
        git_repo.git("switch", "feature")
        git_repo.write("untracked.py", "c = 1\n")

        changed = LineScopes(WorkingTree.at(git_repo.root)).changed_lines("main")

        assert changed == ChangedLines(
            {
                "committed.py": FileDiff(
                    base_path=None,
                    added_lines=frozenset({1}),
                    deletion_points=frozenset(),
                    removals=(),
                    head_lines_by_base_line={},
                    removed_base_lines=frozenset(),
                ),
                "untracked.py": FileDiff(
                    base_path=None,
                    added_lines=frozenset({1}),
                    deletion_points=frozenset(),
                    removals=(),
                    head_lines_by_base_line={},
                    removed_base_lines=frozenset(),
                ),
            },
            base=merge_base,
        )

    def test_staged_edit_keeps_the_head_line_of_every_unchanged_base_line(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = "".join(f"x{i} = {i}\n" for i in range(1, 11))
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("x10 = 10", "x10 = 0"))
        git_repo.git("add", "a.py")

        changed = LineScopes(WorkingTree.at(git_repo.root)).changed_lines("HEAD")

        assert changed == ChangedLines(
            {
                "a.py": FileDiff(
                    base_path="a.py",
                    added_lines=frozenset({10}),
                    deletion_points=frozenset(),
                    removals=(
                        Removal(
                            shown_before=10,
                            reported_line=10,
                            rows=(RemovedRow(10, text=b"x10 = 10"),),
                        ),
                    ),
                    head_lines_by_base_line={line: line for line in range(1, 10)},
                    removed_base_lines=frozenset({10}),
                )
            },
            base=git_repo.head(),
        )

    def test_changed_lines_are_the_added_and_modified_lines(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\nb = 1\nc = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "a = 1\nb = 2\nc = 1\nd = 1\n")

        changed = LineScopes(WorkingTree.at(git_repo.root)).changed_lines("HEAD")

        assert changed == ChangedLines(
            {
                "a.py": FileDiff(
                    base_path="a.py",
                    added_lines=frozenset({2, 4}),
                    deletion_points=frozenset(),
                    removals=(
                        Removal(
                            shown_before=2, reported_line=2, rows=(RemovedRow(2, text=b"b = 1"),)
                        ),
                    ),
                    head_lines_by_base_line={1: 1, 3: 3},
                    removed_base_lines=frozenset({2}),
                )
            },
            base=git_repo.head(),
        )

    def test_change_of_only_blank_lines_changes_no_file(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\n\nb = 1\n")
        git_repo.write("b.py", "a = 1\nb = 1\n")
        git_repo.commit("Add a and b")
        git_repo.write("a.py", "a = 1\n\n\n  \nb = 1\n")
        git_repo.write("b.py", "a = 1\n\nb = 1\n")
        git_repo.write("c.py", "\n\n")

        changed = LineScopes(WorkingTree.at(git_repo.root)).changed_lines("HEAD")

        assert changed == ChangedLines({}, base=git_repo.head())

    def test_only_a_newline_ends_a_changed_line(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "a = 1\n\x0cdef f():\n    s = 'p\u2028+q\r+r'\n    return 2\n")

        changed = LineScopes(WorkingTree.at(git_repo.root)).changed_lines("HEAD")

        assert changed == ChangedLines(
            {
                "a.py": FileDiff(
                    base_path="a.py",
                    added_lines=frozenset({2, 3, 4}),
                    deletion_points=frozenset(),
                    removals=(),
                    head_lines_by_base_line={1: 1},
                    removed_base_lines=frozenset(),
                )
            },
            base=git_repo.head(),
        )

    def test_line_of_non_ascii_space_is_a_changed_line_in_tracked_and_untracked_files(
        self, tmp_path
    ):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "a = 1\n\u00a0\n")
        git_repo.write("b.py", "\u00a0\n")

        changed = LineScopes(WorkingTree.at(git_repo.root)).changed_lines("HEAD")

        assert changed == ChangedLines(
            {
                "a.py": FileDiff(
                    base_path="a.py",
                    added_lines=frozenset({2}),
                    deletion_points=frozenset(),
                    removals=(),
                    head_lines_by_base_line={1: 1},
                    removed_base_lines=frozenset(),
                ),
                "b.py": FileDiff(
                    base_path=None,
                    added_lines=frozenset({1}),
                    deletion_points=frozenset(),
                    removals=(),
                    head_lines_by_base_line={},
                    removed_base_lines=frozenset(),
                ),
            },
            base=git_repo.head(),
        )

    def test_changed_file_whose_name_holds_a_space_keeps_its_name(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("x y.py", "a = 1\n")
        git_repo.commit("Add x y")
        git_repo.write("x y.py", "a = 2\n")

        changed = LineScopes(WorkingTree.at(git_repo.root)).changed_lines("HEAD")

        assert changed == ChangedLines(
            {
                "x y.py": FileDiff(
                    base_path="x y.py",
                    added_lines=frozenset({1}),
                    deletion_points=frozenset(),
                    removals=(
                        Removal(
                            shown_before=1, reported_line=1, rows=(RemovedRow(1, text=b"a = 1"),)
                        ),
                    ),
                    head_lines_by_base_line={},
                    removed_base_lines=frozenset({1}),
                )
            },
            base=git_repo.head(),
        )

    def test_renamed_file_keeps_its_base_path(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = "".join(f"x{i} = {i}\n" for i in range(10))
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.git("mv", "a.py", "b.py")
        git_repo.write("b.py", source.replace("x9 = 9", "x9 = 10"))

        changed = LineScopes(WorkingTree.at(git_repo.root)).changed_lines("HEAD")

        assert changed == ChangedLines(
            {
                "b.py": FileDiff(
                    base_path="a.py",
                    added_lines=frozenset({10}),
                    deletion_points=frozenset(),
                    removals=(
                        Removal(
                            shown_before=10,
                            reported_line=10,
                            rows=(RemovedRow(10, text=b"x9 = 9"),),
                        ),
                    ),
                    head_lines_by_base_line={line: line for line in range(1, 10)},
                    removed_base_lines=frozenset({10}),
                )
            },
            base=git_repo.head(),
        )

    def test_untracked_file_has_every_line_with_code_changed(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\n\nb = 1\n")

        changed = LineScopes(WorkingTree.at(git_repo.root)).changed_lines("HEAD")

        assert changed == ChangedLines(
            {
                "a.py": FileDiff(
                    base_path=None,
                    added_lines=frozenset({1, 3}),
                    deletion_points=frozenset(),
                    removals=(),
                    head_lines_by_base_line={},
                    removed_base_lines=frozenset(),
                )
            },
            base=git_repo.head(),
        )

    def test_removed_row_that_is_not_utf_8_keeps_its_bytes(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        (git_repo.root / "a.py").write_bytes(b"a = 1\nb = '\xff'\n")
        git_repo.commit("Add a")
        (git_repo.root / "a.py").write_bytes(b"a = 1\n")

        changed = LineScopes(WorkingTree.at(git_repo.root)).changed_lines("HEAD")

        assert changed == ChangedLines(
            {
                "a.py": FileDiff(
                    base_path="a.py",
                    added_lines=frozenset(),
                    deletion_points=frozenset({1}),
                    removals=(
                        Removal(
                            shown_before=2,
                            reported_line=1,
                            rows=(RemovedRow(2, text=b"b = '\xff'"),),
                        ),
                    ),
                    head_lines_by_base_line={1: 1},
                    removed_base_lines=frozenset({2}),
                )
            },
            base=git_repo.head(),
        )

    def test_removed_row_ending_in_crlf_drops_the_carriage_return(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        (git_repo.root / "a.py").write_bytes(b"a = 1\r\nb = 1\r\n")
        git_repo.commit("Add a")
        (git_repo.root / "a.py").write_bytes(b"a = 1\r\n")

        changed = LineScopes(WorkingTree.at(git_repo.root)).changed_lines("HEAD")

        assert changed == ChangedLines(
            {
                "a.py": FileDiff(
                    base_path="a.py",
                    added_lines=frozenset(),
                    deletion_points=frozenset({1}),
                    removals=(
                        Removal(
                            shown_before=2, reported_line=1, rows=(RemovedRow(2, text=b"b = 1"),)
                        ),
                    ),
                    head_lines_by_base_line={1: 1},
                    removed_base_lines=frozenset({2}),
                )
            },
            base=git_repo.head(),
        )

    def test_all_lines_has_tracked_and_untracked_files(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("tracked.py", "")
        git_repo.write("deleted.py", "")
        git_repo.commit("Add modules")
        (git_repo.root / "deleted.py").unlink()
        git_repo.write("untracked.py", "")

        scope = LineScopes(WorkingTree.at(git_repo.root)).all_lines()

        assert scope == AllLines(("tracked.py", "untracked.py"))


class TestChangedLines:
    def test_covers_a_changed_line(self, make_line_range):
        changed = ChangedLines({"a.py": FileDiff.of_new_file(b"\na = 1\n")})

        assert changed.covers("a.py", make_line_range(start=2))

    def test_does_not_cover_an_unchanged_line(self, make_line_range):
        changed = ChangedLines({"a.py": FileDiff.of_new_file(b"\na = 1\n")})

        assert not changed.covers("a.py", make_line_range(start=1))

    def test_does_not_cover_an_unchanged_file(self, make_line_range):
        changed = ChangedLines({"a.py": FileDiff.of_new_file(b"\na = 1\n")})

        assert not changed.covers("b.py", make_line_range(start=2))

    def test_covers_the_whole_of_a_changed_file(self):
        changed = ChangedLines({"a.py": FileDiff.of_new_file(b"\na = 1\n")})

        assert changed.covers("a.py", None)

    def test_does_not_cover_the_whole_of_an_unchanged_file(self):
        changed = ChangedLines({"a.py": FileDiff.of_new_file(b"\na = 1\n")})

        assert not changed.covers("b.py", None)

    def test_covers_a_range_that_contains_a_changed_line(self, make_line_range):
        changed = ChangedLines({"a.py": FileDiff.of_new_file(b"\n\na = 1\n")})

        assert changed.covers("a.py", make_line_range(start=2, end=4))

    def test_does_not_cover_a_range_without_a_changed_line(self, make_line_range):
        changed = ChangedLines({"a.py": FileDiff.of_new_file(b"\n\n\n\na = 1\n")})

        assert not changed.covers("a.py", make_line_range(start=2, end=4))

    def test_covers_a_range_that_contains_a_deletion_point(self, make_line_range):
        rows = [KeptRow(1, 1), KeptRow(2, 2), KeptRow(3, 3), RemovedRow(4, text=b"d = 1")]
        changed = ChangedLines({"a.py": FileDiff.from_whole_file_rows("a.py", rows)})

        assert changed.covers("a.py", make_line_range(start=2, end=4))

    def test_covers_a_deletion_point(self, make_line_range):
        rows = [KeptRow(1, 1), KeptRow(2, 2), KeptRow(3, 3), RemovedRow(4, text=b"d = 1")]
        changed = ChangedLines({"a.py": FileDiff.from_whole_file_rows("a.py", rows)})

        assert changed.covers("a.py", make_line_range(start=3))
