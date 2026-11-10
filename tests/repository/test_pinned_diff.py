import pytest
from git_repo import GitRepo

from codeguard.repository.git import Git
from codeguard.repository.pinned_diff import PinnedDiff
from codeguard.repository.unified_diff import Hunk


class TestPinnedDiff:
    def test_hunks_hold_only_the_changed_rows(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\nb = 1\nc = 1\nd = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "a = 1\nb = 2\nc = 1\nd = 1\n")

        hunks = PinnedDiff(Git(git_repo.root)).hunks(git_repo.head())

        assert hunks == (Hunk("a.py", "a.py", 2, 1, 2, 1, added=("b = 2",), removed=("b = 1",)),)

    def test_deleted_file_has_no_hunks(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\n")
        git_repo.commit("Add a")
        (git_repo.root / "a.py").unlink()

        assert PinnedDiff(Git(git_repo.root)).hunks(git_repo.head()) == ()

    def test_hunks_are_those_of_the_default_diff_algorithm_whatever_git_config_sets(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "x = f()\n}\nreturn x\nreturn x\nb = 2\nreturn x\npass\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "x = f()\n}\npass\n}\na = 1\nreturn x\nreturn x\n")
        git_repo.git("config", "diff.algorithm", "patience")

        hunks = PinnedDiff(Git(git_repo.root)).hunks(git_repo.head())

        assert hunks == (
            Hunk("a.py", "a.py", 2, 0, 3, 3, added=("pass", "}", "a = 1"), removed=()),
            Hunk("a.py", "a.py", 5, 3, 7, 0, added=(), removed=("b = 2", "return x", "pass")),
        )

    def test_added_rows_are_placed_by_the_indent_heuristic_whatever_git_config_sets(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "def f():\ndef f():\n    x = 1\ndef f():\ndef f():\ndef f():\n")
        git_repo.commit("Add a")
        git_repo.write(
            "a.py",
            "def f():\ndef f():\ndef f():\ndef f():\n    x = 1\ndef f():\ndef f():\ndef f():\n",
        )
        git_repo.git("config", "diff.indentHeuristic", "false")

        hunks = PinnedDiff(Git(git_repo.root)).hunks(git_repo.head())

        assert hunks == (
            Hunk("a.py", "a.py", 1, 0, 2, 2, added=("def f():", "def f():"), removed=()),
        )

    def test_nearby_changes_stay_apart_when_git_config_joins_their_hunks(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\nb = 1\nc = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "a = 2\nb = 1\nc = 2\n")
        git_repo.git("config", "diff.interHunkContext", "1")

        hunks = PinnedDiff(Git(git_repo.root)).hunks(git_repo.head())

        assert hunks == (
            Hunk("a.py", "a.py", 1, 1, 1, 1, added=("a = 2",), removed=("a = 1",)),
            Hunk("a.py", "a.py", 3, 1, 3, 1, added=("c = 2",), removed=("c = 1",)),
        )

    def test_rows_are_the_file_rows_when_git_config_converts_its_text(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\nb = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "a = 1\nb = 2\n")
        git_repo.write(".git/info/attributes", "*.py diff=headed\n")
        git_repo.git("config", "diff.headed.textconv", "sh -c 'echo header; cat \"$0\"'")

        hunks = PinnedDiff(Git(git_repo.root)).hunks(git_repo.head())

        assert hunks == (Hunk("a.py", "a.py", 2, 1, 2, 1, added=("b = 2",), removed=("b = 1",)),)

    def test_renamed_file_is_diffed_from_its_base_path_when_git_config_turns_off_renames(
        self, tmp_path
    ):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = "".join(f"x{i} = {i}\n" for i in range(10))
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.git("mv", "a.py", "b.py")
        git_repo.write("b.py", source.replace("x9 = 9", "x9 = 10"))
        git_repo.git("config", "diff.renames", "false")

        hunks = PinnedDiff(Git(git_repo.root)).hunks(git_repo.head())

        assert hunks == (
            Hunk("b.py", "a.py", 10, 1, 10, 1, added=("x9 = 10",), removed=("x9 = 9",)),
        )

    def test_copied_file_is_new_when_git_config_finds_copies(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = "".join(f"x{i} = {i}\n" for i in range(30))
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", f"{source}y = 1\n")
        git_repo.write("b.py", f"{source}y = 1\n")
        git_repo.git("add", "b.py")
        git_repo.git("config", "diff.renames", "copies")

        hunks = PinnedDiff(Git(git_repo.root)).hunks(git_repo.head())

        rows = (*(f"x{i} = {i}" for i in range(30)), "y = 1")
        assert hunks == (
            Hunk("a.py", "a.py", 30, 0, 31, 1, added=("y = 1",), removed=()),
            Hunk("b.py", "", 0, 0, 1, 31, added=rows, removed=()),
        )

    def test_renamed_files_are_diffed_from_their_base_paths_when_git_config_lowers_the_limit(
        self, tmp_path
    ):
        git_repo = GitRepo.init(tmp_path.resolve())
        for name in ("a", "b", "c"):
            git_repo.write(f"{name}.py", "".join(f"{name}{i} = {i}\n" for i in range(20)))
        git_repo.commit("Add modules")
        for name in ("a", "b", "c"):
            git_repo.git("mv", f"{name}.py", f"{name}2.py")
            git_repo.write(
                f"{name}2.py", "".join(f"{name}{i} = {i}\n" for i in range(20)) + "z = 1\n"
            )
        git_repo.git("config", "diff.renameLimit", "1")

        hunks = PinnedDiff(Git(git_repo.root)).hunks(git_repo.head())

        assert hunks == tuple(
            Hunk(f"{name}2.py", f"{name}.py", 20, 0, 21, 1, added=("z = 1",), removed=())
            for name in ("a", "b", "c")
        )

    @pytest.mark.parametrize(
        ("setting", "value"), [("diff.submodule", "diff"), ("diff.ignoreSubmodules", "all")]
    )
    def test_moved_submodule_is_one_hunk_of_its_commits_whatever_git_config_sets(
        self, tmp_path, setting, value
    ):
        (tmp_path / "source").mkdir()
        (tmp_path / "repo").mkdir()
        source = GitRepo.init((tmp_path / "source").resolve())
        source.write("a.py", "a = 1\n")
        source.commit("Add a")
        git_repo = GitRepo.init((tmp_path / "repo").resolve())
        git_repo.git(
            "-c", "protocol.file.allow=always", "submodule", "add", str(source.root), "sub"
        )
        git_repo.commit("Add sub")
        submodule = GitRepo(git_repo.root / "sub")
        submodule.write("a.py", "a = 2\n")
        submodule.commit("Change a")
        git_repo.git("config", setting, value)

        hunks = PinnedDiff(Git(git_repo.root)).hunks(git_repo.head())

        assert hunks == (
            Hunk(
                "sub",
                "sub",
                1,
                1,
                1,
                1,
                added=(f"Subproject commit {submodule.head()}",),
                removed=(f"Subproject commit {source.head()}",),
            ),
        )
