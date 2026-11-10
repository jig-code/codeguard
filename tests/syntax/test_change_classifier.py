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


def classified_judged_lines(git_repo: GitRepo, file: str) -> frozenset[int] | None:
    working_tree = WorkingTree(git_repo.root)
    classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
    return classifier.classify(working_tree.changed_lines("HEAD")).judged_lines(file)


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

    def test_method_edit_judges_the_method(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write(
            "a.py",
            "class Order:\n    def total(self):\n        return 1\n\n"
            "    def tax(self):\n        return 0\n",
        )
        git_repo.commit("Add a")
        git_repo.write(
            "a.py",
            "class Order:\n    def total(self):\n        return 1\n\n"
            "    def tax(self):\n        return 2\n",
        )

        assert classified_judged_lines(git_repo, "a.py") == {5, 6}

    def test_class_body_edit_outside_a_method_judges_the_class_header_and_the_line(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write(
            "a.py", "class Order:\n    rate = 1\n\n    def tax(self):\n        return 0\n"
        )
        git_repo.commit("Add a")
        git_repo.write(
            "a.py", "class Order:\n    rate = 2\n\n    def tax(self):\n        return 0\n"
        )

        assert classified_judged_lines(git_repo, "a.py") == {1, 2}

    def test_class_body_edit_judges_every_line_of_a_class_header(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = (
            "class Order(\n    Base,\n):\n    def tax(self):\n        return 0\n\n    rate = 1\n"
        )
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("rate = 1", "rate = 2"))

        assert classified_judged_lines(git_repo, "a.py") == {1, 2, 3, 7}

    def test_class_header_edit_judges_the_class(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "class Order:\n    def tax(self):\n        return 0\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "class Order(Base):\n    def tax(self):\n        return 0\n")

        assert classified_judged_lines(git_repo, "a.py") == {1, 2, 3}

    def test_module_level_edit_judges_the_changed_line(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "RATE = 1\n\n\ndef tax():\n    return 0\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "RATE = 2\n\n\ndef tax():\n    return 0\n")

        assert classified_judged_lines(git_repo, "a.py") == {1}

    def test_method_added_to_a_class_judges_the_method(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "class Order:\n    def total(self):\n        return 1\n")
        git_repo.commit("Add a")
        git_repo.write(
            "a.py",
            "class Order:\n    def total(self):\n        return 1\n\n"
            "    def tax(self):\n        return 0\n",
        )

        assert classified_judged_lines(git_repo, "a.py") == {5, 6}

    def test_new_file_judges_every_line_with_code(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "RATE = 2\n\n\ndef tax():\n    return 0\n")

        assert classified_judged_lines(git_repo, "a.py") == {1, 4, 5}

    def test_body_edit_does_not_cover_the_untouched_first_line_of_its_function(
        self, make_line_range, tmp_path
    ):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "class Order:\n    def total(self):\n        return 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "class Order:\n    def total(self):\n        return 2\n")
        working_tree = WorkingTree(git_repo.root)
        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)

        scope = classifier.classify(working_tree.changed_lines("HEAD"))

        assert scope.covers("a.py", make_line_range(start=3))
        assert not scope.covers("a.py", make_line_range(start=1))
        assert not scope.covers("a.py", make_line_range(start=2))

    def test_judged_lines_for_a_trigger_take_in_its_node_around_the_change(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = "try:\n    import fast\nexcept ImportError:\n    fast = None\n"
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("fast = None", "fast = False"))
        working_tree = WorkingTree(git_repo.root)
        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)

        scope = classifier.classify(working_tree.changed_lines("HEAD"))

        assert scope.judged_lines("a.py") == {3, 4}
        assert scope.judged_lines("a.py", frozenset({ChangeKind.CONTROL_FLOW})) == {1, 2, 3, 4}

    def test_decorator_edit_judges_the_decorated_method(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = "class Order:\n    @property\n    def total(self):\n        return 1\n"
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("@property", "@cached_property"))

        assert classified_judged_lines(git_repo, "a.py") == {2, 3, 4}

    def test_class_body_edit_judges_the_class_decorators_with_its_header(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = "@dataclass\nclass Order:\n    def tax(self):\n        return 0\n\n    rate = 1\n"
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("rate = 1", "rate = 2"))

        assert classified_judged_lines(git_repo, "a.py") == {1, 2, 6}

    def test_multi_line_statement_edit_judges_the_whole_statement(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = "RATES = {\n    'net': 1,\n    'gross': 2,\n}\nTAX = 3\n"
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("'gross': 2", "'gross': 4"))

        assert classified_judged_lines(git_repo, "a.py") == {1, 2, 3, 4}

    def test_multi_line_statement_edit_in_a_class_body_judges_the_header_and_statement(
        self, tmp_path
    ):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = (
            "class Order:\n    def tax(self):\n        return 0\n\n"
            "    rates = (\n        1,\n        2,\n    )\n"
        )
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("        2,", "        4,"))

        assert classified_judged_lines(git_repo, "a.py") == {1, 5, 6, 7, 8}

    def test_removed_method_judges_the_class_header_not_the_method_before_it(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write(
            "a.py",
            "class Order:\n    def total(self):\n        raise ValueError\n\n"
            "    def tax(self):\n        return 0\n",
        )
        git_repo.commit("Add a")
        git_repo.write("a.py", "class Order:\n    def total(self):\n        raise ValueError\n")

        kinds = classified_kinds(git_repo, "a.py")

        assert classified_judged_lines(git_repo, "a.py") == {1}
        assert kinds is not None
        assert ChangeKind.RETURN_YIELD in kinds
        assert ChangeKind.RAISE not in kinds

    def test_removed_first_member_judges_the_class_header_not_the_class(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write(
            "a.py",
            "class Order:\n    rate = 1\n\n    def tax(self):\n        return 0\n",
        )
        git_repo.commit("Add a")
        git_repo.write("a.py", "class Order:\n\n    def tax(self):\n        return 0\n")

        assert classified_judged_lines(git_repo, "a.py") == {1}

    def test_removed_line_in_a_function_judges_the_function(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "def tax():\n    log()\n    return 0\n\n\nRATE = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "def tax():\n    return 0\n\n\nRATE = 1\n")

        assert classified_judged_lines(git_repo, "a.py") == {1, 2}

    def test_removed_module_level_statement_judges_no_line_beside_it(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "def tax():\n    return 0\n\n\nRATE = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "def tax():\n    return 0\n")

        assert classified_judged_lines(git_repo, "a.py") == frozenset()

    def test_removed_line_of_a_multi_line_statement_judges_the_rest_of_the_statement(
        self, tmp_path
    ):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "TAX = 3\nRATES = (\n    1,\n    2,\n)\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "TAX = 3\nRATES = (\n    1,\n)\n")

        assert classified_judged_lines(git_repo, "a.py") == {2, 3, 4}

    def test_removal_judges_its_context_where_earlier_changes_moved_it(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "A = 1\n\n\ndef tax():\n    log()\n    return 0\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "A = 1\nB = 2\nC = 3\n\n\ndef tax():\n    return 0\n")

        assert classified_judged_lines(git_repo, "a.py") == {2, 3, 6, 7}

    def test_handler_header_edit_judges_the_handler_and_the_block_it_guards(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = (
            "try:\n    load()\nexcept KeyError:\n    pass\n"
            "except ValueError:\n    retry()\nfinally:\n    close()\n"
        )
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("except ValueError:", "except TypeError:"))

        assert classified_judged_lines(git_repo, "a.py") == {1, 2, 5, 6}

    def test_handler_is_judged_with_its_own_try_block_not_a_nested_one(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = (
            "try:\n    load()\nexcept KeyError:\n    try:\n        fetch()\n"
            "    except OSError:\n        pass\nexcept ValueError:\n    retry()\n"
        )
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("except ValueError:", "except TypeError:"))

        assert classified_judged_lines(git_repo, "a.py") == {1, 2, 8, 9}

    def test_else_header_edit_judges_only_its_clause(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = "if fast:\n    run()\nelif slow:\n    wait()\nelse:\n    stop()\n"
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("elif slow:", "elif late:"))

        assert classified_judged_lines(git_repo, "a.py") == {3, 4}

    def test_comment_edit_judges_only_the_comment(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = "def tax():\n    # net\n    return 0\n"
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("# net", "# gross"))

        assert classified_judged_lines(git_repo, "a.py") == {2}
        assert classified_kinds(git_repo, "a.py") == {ChangeKind.COMMENT, ChangeKind.ANY}

    def test_removed_comment_judges_no_code(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        git_repo.write("a.py", "def tax():\n    # net\n    return 0\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "def tax():\n    return 0\n")

        assert classified_judged_lines(git_repo, "a.py") == frozenset()
        assert classified_kinds(git_repo, "a.py") == {ChangeKind.COMMENT, ChangeKind.ANY}

    def test_docstring_edit_judges_only_the_docstring(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = 'def tax():\n    """Net tax."""\n    return 0\n'
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("Net", "Gross"))

        assert classified_judged_lines(git_repo, "a.py") == {2}
        assert classified_kinds(git_repo, "a.py") == {ChangeKind.DOCSTRING, ChangeKind.ANY}

    def test_module_docstring_edit_touches_no_code_kind(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = '"""Pricing.\n\nRates.\n"""  # doc\nRATE = 1\n'
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("Rates.", "Tax rates."))

        assert classified_judged_lines(git_repo, "a.py") == {3}
        assert classified_kinds(git_repo, "a.py") == {ChangeKind.DOCSTRING, ChangeKind.ANY}

    def test_docstring_after_a_shebang_is_a_docstring(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = '#!/usr/bin/env python\n"""Pricing.\n\nRates.\n"""\nRATE = 1\n'
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("Rates.", "Tax rates."))

        assert classified_judged_lines(git_repo, "a.py") == {4}
        assert classified_kinds(git_repo, "a.py") == {ChangeKind.DOCSTRING, ChangeKind.ANY}

    def test_comment_edit_takes_in_no_trigger_node_around_it(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = "if fast:\n    # net\n    run()\n"
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("net", "gross"))
        working_tree = WorkingTree(git_repo.root)
        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)

        scope = classifier.classify(working_tree.changed_lines("HEAD"))

        assert scope.judged_lines("a.py", frozenset({ChangeKind.CONTROL_FLOW})) == {2}

    def test_removed_statement_in_a_module_level_block_judges_the_block_header(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = "if debug:\n    log()\n    run()\nelse:\n    stop()\n"
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("    log()\n", ""))

        assert classified_judged_lines(git_repo, "a.py") == {1}

    def test_removed_handler_judges_its_try_and_the_block_it_guarded(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = "try:\n    load()\nexcept KeyError:\n    pass\nfinally:\n    close()\n"
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("except KeyError:\n    pass\n", ""))

        assert classified_judged_lines(git_repo, "a.py") == {1, 2}

    def test_removal_in_a_renamed_file_judges_its_context(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = (
            "".join(f"X{i} = {i}\n" for i in range(20)) + "def tax():\n    log()\n    return 0\n"
        )
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.git("mv", "a.py", "b.py")
        git_repo.write("b.py", source.replace("    log()\n", ""))

        assert classified_judged_lines(git_repo, "b.py") == {21, 22}
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

        assert classified_judged_lines(git_repo, "0.py") == {21, 22}
        assert ChangeKind.DEFINITION_ADDED_OR_REMOVED not in (
            classified_kinds(git_repo, "0.py") or ()
        )

    def test_removed_one_line_handler_judges_its_try_and_the_block_it_guarded(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = "try:\n    load()\n    run()\nexcept KeyError: pass\nclose()\n"
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("except KeyError: pass\n", ""))

        assert classified_judged_lines(git_repo, "a.py") == {1, 2, 3}

    def test_removed_function_in_a_module_level_block_judges_the_block_header(self, tmp_path):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = "if typing:\n    def f():\n        load()\n    rate = 1\n"
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("    def f():\n        load()\n", ""))

        assert classified_judged_lines(git_repo, "a.py") == {1}

    def test_class_body_edit_no_statement_holds_judges_the_class_header_and_the_line(
        self, tmp_path
    ):
        git_repo = GitRepo.init(tmp_path.resolve())
        source = "class A:\n    x = 1\n    y = 2\n\n    def g(self):\n        pass\n"
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("    y = 2\n", "    y =\n"))

        assert classified_judged_lines(git_repo, "a.py") == {1, 3}
