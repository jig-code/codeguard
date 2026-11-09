from git_repo import GitRepo

from codeguard.working_tree import AllLines, ChangedLines, Edit, WorkingTree


class TestWorkingTree:
    def test_containing_resolves_top_level_from_subdirectory(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("pkg/module.py", "")

        working_tree = WorkingTree.containing(git_repo.root / "pkg")

        assert working_tree == WorkingTree(root=git_repo.root)

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

        changed = WorkingTree(root=git_repo.root).changed_lines("HEAD")

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

        changed = WorkingTree(root=git_repo.root).changed_lines("main")

        assert changed.files == ("committed.py", "untracked.py")

    def test_changed_lines_are_the_added_and_modified_lines(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\nb = 1\nc = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "a = 1\nb = 2\nc = 1\nd = 1\n")

        changed = WorkingTree(root=git_repo.root).changed_lines("HEAD")

        assert changed == ChangedLines(
            {"a.py": frozenset({2, 4})},
            removed={"a.py": frozenset({2})},
            edits={"a.py": (Edit(2, 1, 2, 1), Edit(3, 0, 4, 1))},
            base=git_repo.head(),
        )

    def test_added_blank_lines_are_not_changed_lines(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "class A:\n    x = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "class A:\n    x = 1\n\n    def y(self):\n        pass\n")

        changed = WorkingTree(root=git_repo.root).changed_lines("HEAD")

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

        changed = WorkingTree(root=git_repo.root).changed_lines("HEAD")

        assert changed == ChangedLines({}, base=git_repo.head())

    def test_code_replaced_by_blank_lines_is_a_deletion_point_after_the_line_before_it(
        self, tmp_path
    ):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\nb = 1\nc = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "a = 1\n\nc = 1\n")

        changed = WorkingTree(root=git_repo.root).changed_lines("HEAD")

        assert changed == ChangedLines(
            lines={},
            deletions={"a.py": frozenset({1})},
            removed={"a.py": frozenset({2})},
            edits={"a.py": (Edit(2, 1, 2, 1),)},
            base=git_repo.head(),
        )

    def test_removed_blank_lines_are_not_a_deletion_point(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\n\n\nb = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "a = 1\n\nb = 1\n")

        changed = WorkingTree(root=git_repo.root).changed_lines("HEAD")

        assert changed == ChangedLines({}, base=git_repo.head())

    def test_code_replaced_by_a_blank_first_line_is_a_deletion_point_on_line_1(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "import os\nb = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "\nb = 1\n")

        changed = WorkingTree(root=git_repo.root).changed_lines("HEAD")

        assert changed == ChangedLines(
            lines={},
            deletions={"a.py": frozenset({1})},
            removed={"a.py": frozenset({1})},
            edits={"a.py": (Edit(1, 1, 1, 1),)},
            base=git_repo.head(),
        )

    def test_only_a_newline_ends_a_changed_line(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "a = 1\n\x0cdef f():\n    s = 'p\u2028+q\r+r'\n    return 2\n")

        changed = WorkingTree(root=git_repo.root).changed_lines("HEAD")

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

        changed = WorkingTree(root=git_repo.root).changed_lines("HEAD")

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

        changed = WorkingTree(root=git_repo.root).changed_lines("HEAD")

        assert changed == ChangedLines(
            {"x y.py": frozenset({1})},
            removed={"x y.py": frozenset({1})},
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

        changed = WorkingTree(root=git_repo.root).changed_lines("HEAD")

        assert changed.sources == {"b.py": "a.py"}
        assert changed.base_path("b.py") == "a.py"

    def test_untracked_file_has_no_base_path(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\n")
        git_repo.commit("Add a")
        git_repo.write("b.py", "b = 1\n")

        assert WorkingTree(root=git_repo.root).changed_lines("HEAD").base_path("b.py") is None

    def test_untracked_file_has_every_line_with_code_changed(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\n\nb = 1\n")

        changed = WorkingTree(root=git_repo.root).changed_lines("HEAD")

        assert changed == ChangedLines({"a.py": frozenset({1, 3})}, base=git_repo.head())

    def test_untracked_nested_repository_is_not_read_as_a_file(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        nested = git_repo.root / "nested"
        nested.mkdir()
        nested_repo = GitRepo.init(nested)
        nested_repo.write("module.py", "value = 1\n")
        git_repo.write("new/module.py", "value = 2\n")

        changed = WorkingTree(root=git_repo.root).changed_lines("HEAD")

        assert changed == ChangedLines({"new/module.py": frozenset({1})}, base=git_repo.head())

    def test_removed_lines_are_a_deletion_point_after_the_line_before_them(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\nb = 1\nc = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "a = 1\nc = 1\n")

        changed = WorkingTree(root=git_repo.root).changed_lines("HEAD")

        assert changed == ChangedLines(
            lines={},
            deletions={"a.py": frozenset({1})},
            removed={"a.py": frozenset({2})},
            edits={"a.py": (Edit(2, 1, 1, 0),)},
            base=git_repo.head(),
        )

    def test_diff_is_from_the_base_with_the_function_around_each_change(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write(
            "a.py",
            "import os\nimport sys\n\n\ndef f():\n    a = 1\n    b = 2\n    c = 3\n"
            "    d = 4\n    return a\n\n\ndef g():\n    return 2\n",
        )
        git_repo.commit("Add a")
        git_repo.write(
            "a.py",
            "import re\nimport os\nimport sys\n\n\ndef f():\n    a = 1\n    b = 2\n"
            "    c = 3\n    d = 4\n    return d\n\n\ndef g():\n    return 2\n",
        )

        changed = WorkingTree(root=git_repo.root).changed_lines("HEAD")

        assert changed.diff(git_repo.root, "a.py") == (
            "diff --git a/a.py b/a.py\n"
            "index cf58f90..96c80e9 100644\n"
            "--- a/a.py\n"
            "+++ b/a.py\n"
            "@@ -1,3 +1,4 @@\n"
            "+import re\n"
            " import os\n"
            " import sys\n"
            " \n"
            "@@ -5,9 +6,9 @@\n"
            " def f():\n"
            "     a = 1\n"
            "     b = 2\n"
            "     c = 3\n"
            "     d = 4\n"
            "-    return a\n"
            "+    return d\n"
            " \n"
            " \n"
            " def g():\n"
        )

    def test_diff_of_a_method_edit_holds_the_method_not_its_class(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = (
            "class Order:\n"
            "    def total(self):\n"
            "        return 1\n"
            "\n"
            "    def tax(self):\n"
            "        rate = 2\n"
            "        base = 3\n"
            "        extra = 4\n"
            "        return rate * base + extra\n"
            "\n"
            "    def fee(self):\n"
            "        return 5\n"
        )
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("rate * base + extra", "rate * base"))

        changed = WorkingTree(root=git_repo.root).changed_lines("HEAD")

        assert changed.diff(git_repo.root, "a.py") == (
            "diff --git a/a.py b/a.py\n"
            "index 4cab5d4..4f585fb 100644\n"
            "--- a/a.py\n"
            "+++ b/a.py\n"
            "@@ -5,8 +5,8 @@ def total(self):\n"
            "     def tax(self):\n"
            "         rate = 2\n"
            "         base = 3\n"
            "         extra = 4\n"
            "-        return rate * base + extra\n"
            "+        return rate * base\n"
            " \n"
            "     def fee(self):\n"
            "         return 5\n"
        )

    def test_diff_ignores_the_git_config(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "def f():\n    a = 1\n    return a\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "def f():\n    a = 2\n    return a\n")
        changed = WorkingTree(root=git_repo.root).changed_lines("HEAD")
        for setting in ("diff.noprefix", "diff.mnemonicPrefix", "color.diff", "diff.relative"):
            git_repo.git("config", setting, "true")
        git_repo.git("config", "diff.context", "0")
        git_repo.git("config", "diff.algorithm", "patience")

        assert changed.diff(git_repo.root, "a.py") == (
            "diff --git a/a.py b/a.py\n"
            "index 8d5afc4..937b5e7 100644\n"
            "--- a/a.py\n"
            "+++ b/a.py\n"
            "@@ -1,3 +1,3 @@\n"
            " def f():\n"
            "-    a = 1\n"
            "+    a = 2\n"
            "     return a\n"
        )

    def test_diff_of_a_renamed_file_is_from_its_base_path(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = "".join(f"x{i} = {i}\n" for i in range(10))
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.git("mv", "a.py", "b.py")
        git_repo.write("b.py", source.replace("x9 = 9", "x9 = 10"))

        changed = WorkingTree(root=git_repo.root).changed_lines("HEAD")

        assert changed.diff(git_repo.root, "b.py") == (
            "diff --git a/a.py b/b.py\n"
            "similarity index 88%\n"
            "rename from a.py\n"
            "rename to b.py\n"
            "index bf7f0c9..4754884 100644\n"
            "--- a/a.py\n"
            "+++ b/b.py\n"
            "@@ -1,10 +1,10 @@\n" + "".join(f" x{i} = {i}\n" for i in range(9)) + "-x9 = 9\n"
            "+x9 = 10\n"
        )

    def test_diff_of_an_untracked_file_adds_it_whole(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\n\nb = 1\n")

        changed = WorkingTree(root=git_repo.root).changed_lines("HEAD")

        assert changed.diff(git_repo.root, "a.py") == (
            "diff --git a/a.py b/a.py\n"
            "new file mode 100644\n"
            "index 0000000..be1afea\n"
            "--- /dev/null\n"
            "+++ b/a.py\n"
            "@@ -0,0 +1,3 @@\n"
            "+a = 1\n"
            "+\n"
            "+b = 1\n"
        )

    def test_diff_replaces_bytes_that_are_not_utf_8(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        (git_repo.root / "a.py").write_bytes(b"a = '\xff'\n")

        changed = WorkingTree(root=git_repo.root).changed_lines("HEAD")

        assert changed.diff(git_repo.root, "a.py") == (
            "diff --git a/a.py b/a.py\n"
            "new file mode 100644\n"
            "index 0000000..0885fc8\n"
            "--- /dev/null\n"
            "+++ b/a.py\n"
            "@@ -0,0 +1 @@\n"
            "+a = '\ufffd'\n"
        )

    def test_diff_of_all_lines_adds_a_tracked_file_whole(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\n")
        git_repo.commit("Add a")

        scope = WorkingTree(root=git_repo.root).all_lines()

        assert scope.diff(git_repo.root, "a.py") == (
            "diff --git a/a.py b/a.py\n"
            "new file mode 100644\n"
            "index 0000000..1337a53\n"
            "--- /dev/null\n"
            "+++ b/a.py\n"
            "@@ -0,0 +1 @@\n"
            "+a = 1\n"
        )

    def test_base_contents_are_the_files_that_exist_in_the_base(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "a = 2\n")
        git_repo.write("new.py", "b = 1\n")

        contents = WorkingTree(root=git_repo.root).base_contents(
            git_repo.head(), ["a.py", "new.py"]
        )

        assert contents == {"a.py": b"a = 1\n"}

    def test_all_lines_has_tracked_and_untracked_files(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("tracked.py", "")
        git_repo.write("deleted.py", "")
        git_repo.commit("Add modules")
        (git_repo.root / "deleted.py").unlink()
        git_repo.write("untracked.py", "")

        scope = WorkingTree(root=git_repo.root).all_lines()

        assert scope == AllLines(("tracked.py", "untracked.py"))


class TestChangedLines:
    def test_covers_a_changed_line(self):
        assert ChangedLines({"a.py": frozenset({2})}).covers("a.py", 2)

    def test_does_not_cover_an_unchanged_line(self):
        assert not ChangedLines({"a.py": frozenset({2})}).covers("a.py", 1)

    def test_does_not_cover_an_unchanged_file(self):
        assert not ChangedLines({"a.py": frozenset({2})}).covers("b.py", 2)

    def test_covers_the_whole_of_a_changed_file(self):
        assert ChangedLines({"a.py": frozenset({2})}).covers("a.py", None)

    def test_does_not_cover_the_whole_of_an_unchanged_file(self):
        assert not ChangedLines({"a.py": frozenset({2})}).covers("b.py", None)

    def test_covers_a_range_that_contains_a_changed_line(self):
        assert ChangedLines({"a.py": frozenset({3})}).covers("a.py", 2, end_line=4)

    def test_does_not_cover_a_range_without_a_changed_line(self):
        assert not ChangedLines({"a.py": frozenset({5})}).covers("a.py", 2, end_line=4)

    def test_covers_a_range_that_contains_a_deletion_point(self):
        changed = ChangedLines(lines={}, deletions={"a.py": frozenset({3})})

        assert changed.covers("a.py", 2, end_line=4)

    def test_covers_a_deletion_point(self):
        changed = ChangedLines(lines={}, deletions={"a.py": frozenset({3})})

        assert changed.covers("a.py", 3)
