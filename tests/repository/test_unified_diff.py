from codeguard.unified_diff import Hunk, parse


class TestParse:
    def test_hunks_hold_their_files_lines_and_rows(self):
        diff = (
            "diff --git a.py a.py\n"
            "index 1..2 100644\n"
            "--- a.py\n"
            "+++ a.py\n"
            "@@ -2 +2,2 @@\n"
            "-b = 1\n"
            "+b = 2\n"
            "+c = 3\n"
            "@@ -5,0 +7 @@\n"
            "+d = 4\n"
        )

        assert parse(diff) == (
            Hunk("a.py", "a.py", 2, 1, 2, 2, added=("b = 2", "c = 3"), removed=("b = 1",)),
            Hunk("a.py", "a.py", 5, 0, 7, 1, added=("d = 4",), removed=()),
        )

    def test_hunks_of_each_file_are_named_after_it(self):
        diff = (
            "diff --git a.py b.py\n"
            "similarity index 90%\n"
            "rename from a.py\n"
            "rename to b.py\n"
            "--- a.py\n"
            "+++ b.py\n"
            "@@ -1 +1 @@\n"
            "-x = 1\n"
            "+x = 2\n"
            "diff --git c.py c.py\n"
            "new file mode 100644\n"
            "--- /dev/null\n"
            "+++ c.py\n"
            "@@ -0,0 +1 @@\n"
            "+y = 1\n"
        )

        assert parse(diff) == (
            Hunk("b.py", "a.py", 1, 1, 1, 1, added=("x = 2",), removed=("x = 1",)),
            Hunk("c.py", "", 0, 0, 1, 1, added=("y = 1",), removed=()),
        )

    def test_a_name_holding_a_space_drops_the_tab_git_ends_it_with(self):
        diff = "diff --git x y.py x y.py\n--- x y.py\t\n+++ x y.py\t\n@@ -1 +1 @@\n-a\n+b\n"

        assert parse(diff) == (Hunk("x y.py", "x y.py", 1, 1, 1, 1, added=("b",), removed=("a",)),)

    def test_a_removed_row_that_looks_like_a_file_header_is_a_row(self):
        diff = "diff --git a.py a.py\n--- a.py\n+++ a.py\n@@ -1 +0,0 @@\n--- x\n"

        assert parse(diff) == (Hunk("a.py", "a.py", 1, 1, 0, 0, added=(), removed=("-- x",)),)

    def test_no_newline_marker_is_not_a_row(self):
        diff = (
            "diff --git a.py a.py\n--- a.py\n+++ a.py\n@@ -1 +1 @@\n-a\n"
            "\\ No newline at end of file\n+b\n\\ No newline at end of file\n"
        )

        assert parse(diff) == (Hunk("a.py", "a.py", 1, 1, 1, 1, added=("b",), removed=("a",)),)

    def test_empty_diff_has_no_hunks(self):
        assert parse("") == ()
