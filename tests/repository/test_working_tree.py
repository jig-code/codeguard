from git_repo import GitRepo

from codeguard.repository import WorkingTree


class TestWorkingTree:
    def test_containing_resolves_top_level_from_subdirectory(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("pkg/module.py", "")

        working_tree = WorkingTree.containing(git_repo.root / "pkg")

        assert working_tree == WorkingTree.at(git_repo.root)

    def test_base_contents_are_the_files_that_exist_in_the_base(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "a = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "a = 2\n")
        git_repo.write("new.py", "b = 1\n")

        contents = WorkingTree.at(git_repo.root).base_contents(git_repo.head(), ["a.py", "new.py"])

        assert contents == {"a.py": b"a = 1\n"}

    def test_merge_base_is_the_commit_head_shares_with_the_base(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        fork = git_repo.head()
        git_repo.git("switch", "--create", "feature")
        git_repo.write("a.py", "a = 1\n")
        git_repo.commit("Add a")

        assert WorkingTree.at(git_repo.root).merge_base("main") == fork

    def test_git_path_is_inside_the_repository_git_directory(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())

        path = WorkingTree.at(git_repo.root).git_path("codeguard.lock")

        assert path == git_repo.root / ".git/codeguard.lock"

    def test_untracked_files_leave_out_ignored_files(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write(".gitignore", "build.log\n")
        git_repo.write("build.log", "done\n")

        assert WorkingTree.at(git_repo.root).untracked_files() == {".gitignore"}

    def test_untracked_files_leave_out_a_directory_that_is_not_a_file(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        nested = git_repo.root / "nested"
        nested.mkdir()
        GitRepo.init(nested)

        assert WorkingTree.at(git_repo.root).untracked_files() == set()

    def test_untracked_files_take_in_a_file_in_a_new_directory(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("pkg/module.py", "a = 1\n")

        assert WorkingTree.at(git_repo.root).untracked_files() == {"pkg/module.py"}

    def test_contents_of_a_symlink_are_its_link_text(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("target.py", "a = 1\n")
        (git_repo.root / "link.py").symlink_to("target.py")

        assert WorkingTree.at(git_repo.root).contents("link.py") == b"target.py"
