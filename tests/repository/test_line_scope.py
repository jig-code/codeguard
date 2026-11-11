from git_repo import GitRepo

from codeguard.repository import AllLines, ChangedLines, Edit, LineScopes, Removal, WorkingTree


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

        assert changed.files == ("staged.py", "unstaged.py", "untracked.py")

    def test_changed_files_from_base_are_changes_since_merge_base(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.git("switch", "--create", "feature")
        git_repo.write("committed.py", "a = 1\n")
        git_repo.commit("Add committed")
        git_repo.git("switch", "main")
        git_repo.write("main_only.py", "b = 1\n")
        git_repo.commit("Add main_only")
        git_repo.git("switch", "feature")
        git_repo.write("untracked.py", "c = 1\n")

        changed = LineScopes(WorkingTree.at(git_repo.root)).changed_lines("main")

        assert changed.files == ("committed.py", "untracked.py")

    def test_changed_lines_are_the_added_and_modified_lines(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\nb = 1\nc = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "a = 1\nb = 2\nc = 1\nd = 1\n")

        changed = LineScopes(WorkingTree.at(git_repo.root)).changed_lines("HEAD")

        assert changed == ChangedLines(
            {"a.py": frozenset({2, 4})},
            removals={"a.py": (Removal(before=2, line=2, rows=("b = 1",), base_lines=(2,)),)},
            edits={"a.py": (Edit(2, 1, 2, 1), Edit(3, 0, 4, 1))},
            base=git_repo.head(),
        )

    def test_added_blank_lines_are_not_changed_lines(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "class A:\n    x = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "class A:\n    x = 1\n\n    def y(self):\n        pass\n")

        changed = LineScopes(WorkingTree.at(git_repo.root)).changed_lines("HEAD")

        assert changed == ChangedLines(
            {"a.py": frozenset({4, 5})}, edits={"a.py": (Edit(2, 0, 3, 3),)}, base=git_repo.head()
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

    def test_code_replaced_by_blank_lines_is_a_deletion_point_after_the_line_before_it(
        self, tmp_path
    ):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\nb = 1\nc = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "a = 1\n\nc = 1\n")

        changed = LineScopes(WorkingTree.at(git_repo.root)).changed_lines("HEAD")

        assert changed == ChangedLines(
            lines={},
            deletions={"a.py": frozenset({1})},
            removals={"a.py": (Removal(before=2, line=1, rows=("b = 1",), base_lines=(2,)),)},
            edits={"a.py": (Edit(2, 1, 2, 1),)},
            base=git_repo.head(),
        )

    def test_removed_blank_lines_are_not_a_deletion_point(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\n\n\nb = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "a = 1\n\nb = 1\n")

        changed = LineScopes(WorkingTree.at(git_repo.root)).changed_lines("HEAD")

        assert changed == ChangedLines({}, base=git_repo.head())

    def test_code_replaced_by_a_blank_first_line_is_a_deletion_point_on_line_1(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "import os\nb = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "\nb = 1\n")

        changed = LineScopes(WorkingTree.at(git_repo.root)).changed_lines("HEAD")

        assert changed == ChangedLines(
            lines={},
            deletions={"a.py": frozenset({1})},
            removals={"a.py": (Removal(before=1, line=1, rows=("import os",), base_lines=(1,)),)},
            edits={"a.py": (Edit(1, 1, 1, 1),)},
            base=git_repo.head(),
        )

    def test_only_a_newline_ends_a_changed_line(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "a = 1\n\x0cdef f():\n    s = 'p\u2028+q\r+r'\n    return 2\n")

        changed = LineScopes(WorkingTree.at(git_repo.root)).changed_lines("HEAD")

        assert changed == ChangedLines(
            {"a.py": frozenset({2, 3, 4})},
            edits={"a.py": (Edit(1, 0, 2, 3),)},
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
            {"a.py": frozenset({2}), "b.py": frozenset({1})},
            edits={"a.py": (Edit(1, 0, 2, 1),)},
            base=git_repo.head(),
        )

    def test_changed_file_whose_name_holds_a_space_keeps_its_name(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("x y.py", "a = 1\n")
        git_repo.commit("Add x y")
        git_repo.write("x y.py", "a = 2\n")

        changed = LineScopes(WorkingTree.at(git_repo.root)).changed_lines("HEAD")

        assert changed == ChangedLines(
            {"x y.py": frozenset({1})},
            removals={"x y.py": (Removal(before=1, line=1, rows=("a = 1",), base_lines=(1,)),)},
            edits={"x y.py": (Edit(1, 1, 1, 1),)},
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

        assert changed.sources == {"b.py": "a.py"}
        assert changed.base_path("b.py") == "a.py"

    def test_untracked_file_has_no_base_path(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\n")
        git_repo.commit("Add a")
        git_repo.write("b.py", "b = 1\n")

        assert (
            LineScopes(WorkingTree.at(git_repo.root)).changed_lines("HEAD").base_path("b.py")
            is None
        )

    def test_untracked_file_has_every_line_with_code_changed(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\n\nb = 1\n")

        changed = LineScopes(WorkingTree.at(git_repo.root)).changed_lines("HEAD")

        assert changed == ChangedLines({"a.py": frozenset({1, 3})}, base=git_repo.head())

    def test_untracked_nested_repository_is_not_read_as_a_file(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        nested = git_repo.root / "nested"
        nested.mkdir()
        nested_repo = GitRepo.init(nested)
        nested_repo.write("module.py", "value = 1\n")
        git_repo.write("new/module.py", "value = 2\n")

        changed = LineScopes(WorkingTree.at(git_repo.root)).changed_lines("HEAD")

        assert changed == ChangedLines({"new/module.py": frozenset({1})}, base=git_repo.head())

    def test_removed_lines_are_a_deletion_point_after_the_line_before_them(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\nb = 1\nc = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "a = 1\nc = 1\n")

        changed = LineScopes(WorkingTree.at(git_repo.root)).changed_lines("HEAD")

        assert changed == ChangedLines(
            lines={},
            deletions={"a.py": frozenset({1})},
            removals={"a.py": (Removal(before=2, line=1, rows=("b = 1",), base_lines=(2,)),)},
            edits={"a.py": (Edit(2, 1, 1, 0),)},
            base=git_repo.head(),
        )

    def test_removed_row_that_is_not_utf_8_is_replace_decoded(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        (git_repo.root / "a.py").write_bytes(b"a = 1\nb = '\xff'\n")
        git_repo.commit("Add a")
        (git_repo.root / "a.py").write_bytes(b"a = 1\n")

        changed = LineScopes(WorkingTree.at(git_repo.root)).changed_lines("HEAD")

        [removal] = changed.removals_in("a.py")
        assert removal.rows == ("b = '\ufffd'",)
        assert removal.rows[0].encode()

    def test_removed_row_ending_in_crlf_drops_the_carriage_return(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        (git_repo.root / "a.py").write_bytes(b"a = 1\r\nb = 1\r\n")
        git_repo.commit("Add a")
        (git_repo.root / "a.py").write_bytes(b"a = 1\r\n")

        changed = LineScopes(WorkingTree.at(git_repo.root)).changed_lines("HEAD")

        [removal] = changed.removals_in("a.py")
        assert removal.rows == ("b = 1",)

    def test_head_line_follows_the_edits_before_a_base_line(self):
        changed = ChangedLines(
            {"a.py": frozenset({2, 3})},
            edits={"a.py": (Edit(1, 0, 2, 2), Edit(3, 1, 5, 0))},
        )

        assert [changed.head_line("a.py", line) for line in (1, 2, 3, 4)] == [1, 4, None, 5]

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
        assert ChangedLines({"a.py": frozenset({2})}).covers("a.py", make_line_range(start=2))

    def test_does_not_cover_an_unchanged_line(self, make_line_range):
        assert not ChangedLines({"a.py": frozenset({2})}).covers("a.py", make_line_range(start=1))

    def test_does_not_cover_an_unchanged_file(self, make_line_range):
        assert not ChangedLines({"a.py": frozenset({2})}).covers("b.py", make_line_range(start=2))

    def test_covers_the_whole_of_a_changed_file(self):
        assert ChangedLines({"a.py": frozenset({2})}).covers("a.py", None)

    def test_does_not_cover_the_whole_of_an_unchanged_file(self):
        assert not ChangedLines({"a.py": frozenset({2})}).covers("b.py", None)

    def test_covers_a_range_that_contains_a_changed_line(self, make_line_range):
        assert ChangedLines({"a.py": frozenset({3})}).covers(
            "a.py", make_line_range(start=2, end=4)
        )

    def test_does_not_cover_a_range_without_a_changed_line(self, make_line_range):
        assert not ChangedLines({"a.py": frozenset({5})}).covers(
            "a.py", make_line_range(start=2, end=4)
        )

    def test_covers_a_range_that_contains_a_deletion_point(self, make_line_range):
        changed = ChangedLines(lines={}, deletions={"a.py": frozenset({3})})

        assert changed.covers("a.py", make_line_range(start=2, end=4))

    def test_covers_a_deletion_point(self, make_line_range):
        changed = ChangedLines(lines={}, deletions={"a.py": frozenset({3})})

        assert changed.covers("a.py", make_line_range(start=3))
