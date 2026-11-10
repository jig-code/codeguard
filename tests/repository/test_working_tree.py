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
