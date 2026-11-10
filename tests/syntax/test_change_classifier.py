from git_repo import GitRepo

from codeguard.ast_grep import AstGrep
from codeguard.config import ChangeKind, GateRule, Ruleset
from codeguard.syntax import ChangeClassifier, SyntaxScanner
from codeguard.working_tree import WorkingTree


def classified_kinds(
    git_repo: GitRepo, file: str, gates: dict[str, GateRule] | None = None
) -> frozenset[str] | None:
    working_tree = WorkingTree(git_repo.root)
    classifier = ChangeClassifier(SyntaxScanner(AstGrep(), gates or {}), working_tree)
    return classifier.classify(working_tree.changed_lines("HEAD")).kinds_of(file)


class TestChangeClassifier:
    def test_trailing_comment_edit_touches_every_kind_on_its_line(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "class Order:\n    total = 1  # net\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "class Order:\n    total = 1  # gross\n")

        assert classified_kinds(git_repo, "a.py") == {
            ChangeKind.COMMENT,
            ChangeKind.CLASS_ATTRIBUTE,
            ChangeKind.NUMBER_LITERAL,
            ChangeKind.CODE,
            ChangeKind.ANY,
        }

    def test_comment_line_edit_is_not_a_code_change(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "# net\nx = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "# gross\nx = 1\n")

        assert classified_kinds(git_repo, "a.py") == {ChangeKind.COMMENT, ChangeKind.ANY}

    def test_body_only_edit_does_not_touch_the_class_header(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "class Order(Base):\n    def total(self):\n        return 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "class Order(Base):\n    def total(self):\n        return 2\n")

        kinds = classified_kinds(git_repo, "a.py")

        assert kinds is not None
        assert ChangeKind.FUNCTION_BODY in kinds
        assert ChangeKind.CLASS_HEADER not in kinds

    def test_new_file_touches_the_kinds_it_contains_and_no_others(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("test_a.py", "def test_total():\n    assert total() == 1\n")

        assert classified_kinds(git_repo, "test_a.py") == {
            ChangeKind.TEST_FUNCTION,
            ChangeKind.FUNCTION_SIGNATURE,
            ChangeKind.FUNCTION_BODY,
            ChangeKind.ASSERT,
            ChangeKind.CALL,
            ChangeKind.NUMBER_LITERAL,
            ChangeKind.DEFINITION_ADDED_OR_REMOVED,
            ChangeKind.CODE,
            ChangeKind.ANY,
        }

    def test_removed_function_is_a_definition_removed(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "x = 1\n\n\ndef total():\n    return 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "x = 1\n")

        kinds = classified_kinds(git_repo, "a.py")

        assert kinds is not None
        assert ChangeKind.DEFINITION_ADDED_OR_REMOVED in kinds

    def test_edited_function_is_not_a_definition_added_or_removed(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "def total():\n    return 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "def total():\n    return 2\n")

        kinds = classified_kinds(git_repo, "a.py")

        assert kinds is not None
        assert ChangeKind.DEFINITION_ADDED_OR_REMOVED not in kinds

    def test_change_inside_a_gate_match_touches_the_gate(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "label = status.name\ncode = status.name\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "label = status.name\ncode = status.value\n")
        gate = GateRule(id="enum-value", language="python", rule={"pattern": "$X.value"})

        kinds = classified_kinds(git_repo, "a.py", {"gate:enum-value": gate})

        assert kinds is not None
        assert "gate:enum-value" in kinds

    def test_change_outside_a_gate_match_does_not_touch_the_gate(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "label = status.name\ncode = status.value\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "label = status.title\ncode = status.value\n")
        gate = GateRule(id="enum-value", language="python", rule={"pattern": "$X.value"})

        kinds = classified_kinds(git_repo, "a.py", {"gate:enum-value": gate})

        assert kinds is not None
        assert "gate:enum-value" not in kinds

    def test_for_rulesets_touches_a_rulesets_gate(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write(
            "python/gates/enum-value.yml",
            "id: enum-value\nlanguage: python\nrule:\n  pattern: $X.value\n",
        )
        git_repo.write("a.py", "label = status.name\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "label = status.value\n")
        working_tree = WorkingTree(git_repo.root)
        ruleset = Ruleset(name="example/python", root=git_repo.root / "python")
        classifier = ChangeClassifier.for_rulesets(AstGrep(), [ruleset], working_tree)

        changed = classifier.classify(working_tree.changed_lines("HEAD"))

        kinds = changed.kinds_of("a.py")
        assert kinds is not None
        assert "gate:example/python/enum-value" in kinds

    def test_fixture_is_its_own_kind(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("conftest.py", "@pytest.fixture\ndef order():\n    return Order()\n")

        kinds = classified_kinds(git_repo, "conftest.py")

        assert kinds is not None
        assert ChangeKind.FIXTURE in kinds
        assert ChangeKind.HELPER_FUNCTION not in kinds
        assert ChangeKind.TEST_FUNCTION not in kinds

    def test_body_edit_does_not_cover_the_untouched_first_line_of_its_function(
        self, tmp_path, make_line_range
    ):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "class Order:\n    def total(self):\n        return 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "class Order:\n    def total(self):\n        return 2\n")
        working_tree = WorkingTree(git_repo.root)
        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)

        scope = classifier.classify(working_tree.changed_lines("HEAD"))

        assert scope.covers("a.py", make_line_range(start=3, end=3))
        assert not scope.covers("a.py", make_line_range(start=1, end=1))
        assert not scope.covers("a.py", make_line_range(start=2, end=2))

    def test_removal_in_a_renamed_file_is_classified_against_its_base(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = (
            "".join(f"X{i} = {i}\n" for i in range(20)) + "def tax():\n    log()\n    return 0\n"
        )
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.git("mv", "a.py", "b.py")
        git_repo.write("b.py", source.replace("    log()\n", ""))

        assert ChangeKind.DEFINITION_ADDED_OR_REMOVED not in (
            classified_kinds(git_repo, "b.py") or ()
        )

    def test_renamed_file_keeps_its_base_beside_a_new_file_at_its_old_path(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = (
            "".join(f"X{i} = {i}\n" for i in range(20)) + "def tax():\n    log()\n    return 0\n"
        )
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.git("mv", "a.py", "0.py")
        git_repo.write("0.py", source.replace("    log()\n", ""))
        git_repo.write("a.py", "def rate():\n    return 1\n")

        assert ChangeKind.DEFINITION_ADDED_OR_REMOVED not in (
            classified_kinds(git_repo, "0.py") or ()
        )
