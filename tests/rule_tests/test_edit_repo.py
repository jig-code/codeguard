import subprocess

from codeguard.rule_tests import EditRepo


class TestEditRepo:
    def test_edited_file_holds_its_after_text_over_its_committed_before_text(self, make_edit_case):
        edit = make_edit_case(file="module.py", before="count = 1\n", after="count = 2\n")

        with EditRepo.of(edit.edits()) as repo:
            committed = subprocess.run(
                ["git", "show", "HEAD:module.py"],
                cwd=repo.root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            written = (repo.root / "module.py").read_text()

        assert committed == "count = 1\n"
        assert written == "count = 2\n"

    def test_unchanged_file_is_committed_and_left_out_of_the_change(self, make_edit_case):
        edit = make_edit_case(
            file="shipping/ship.py",
            before="ship(status=Status.SHIPPED)\n",
            unchanged={"shipping/__init__.py": "from shipping.status import Status\n"},
        )

        with EditRepo.of(edit.edits()) as repo:
            status = subprocess.run(
                ["git", "status", "--porcelain", "--untracked-files=all"],
                cwd=repo.root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout

        assert status == " M shipping/ship.py\n"

    def test_new_file_is_left_untracked(self, make_edit_case):
        edit = make_edit_case(file="module.py", before=None)

        with EditRepo.of(edit.edits()) as repo:
            status = subprocess.run(
                ["git", "status", "--porcelain", "--untracked-files=all"],
                cwd=repo.root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout

        assert status == "?? module.py\n"
