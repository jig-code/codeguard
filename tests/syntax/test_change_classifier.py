from codeguard.ast_grep import AstGrep
from codeguard.config import ChangeKind, GateRule, Ruleset
from codeguard.syntax import ChangeClassifier, SyntaxScanner


class TestChangeClassifier:
    def test_trailing_comment_edit_touches_every_kind_on_its_line(
        self, git_repo, working_tree, line_scopes
    ):
        git_repo.write("a.py", "class Order:\n    total = 1  # net\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "class Order:\n    total = 1  # gross\n")

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].kinds == {
            ChangeKind.COMMENT,
            ChangeKind.CLASS_ATTRIBUTE,
            ChangeKind.NUMBER_LITERAL,
            ChangeKind.CODE,
            ChangeKind.ANY,
        }

    def test_comment_line_edit_is_not_a_code_change(self, git_repo, working_tree, line_scopes):
        git_repo.write("a.py", "# net\nx = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "# gross\nx = 1\n")

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].kinds == {ChangeKind.COMMENT, ChangeKind.ANY}

    def test_body_only_edit_does_not_touch_the_class_header(
        self, git_repo, working_tree, line_scopes
    ):
        git_repo.write("a.py", "class Order(Base):\n    def total(self):\n        return 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "class Order(Base):\n    def total(self):\n        return 2\n")

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        kinds = classification["a.py"].kinds
        assert kinds is not None
        assert ChangeKind.FUNCTION_BODY in kinds
        assert ChangeKind.CLASS_HEADER not in kinds

    def test_new_file_touches_the_kinds_it_contains_and_no_others(
        self, git_repo, working_tree, line_scopes
    ):
        git_repo.write("test_a.py", "def test_total():\n    assert total() == 1\n")

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["test_a.py"].kinds == {
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

    def test_removed_function_is_a_definition_removed(self, git_repo, working_tree, line_scopes):
        git_repo.write("a.py", "x = 1\n\n\ndef total():\n    return 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "x = 1\n")

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        kinds = classification["a.py"].kinds
        assert kinds is not None
        assert ChangeKind.DEFINITION_ADDED_OR_REMOVED in kinds

    def test_edited_function_is_not_a_definition_added_or_removed(
        self, git_repo, working_tree, line_scopes
    ):
        git_repo.write("a.py", "def total():\n    return 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "def total():\n    return 2\n")

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        kinds = classification["a.py"].kinds
        assert kinds is not None
        assert ChangeKind.DEFINITION_ADDED_OR_REMOVED not in kinds

    def test_change_inside_a_gate_match_touches_the_gate(self, git_repo, working_tree, line_scopes):
        git_repo.write("a.py", "label = status.name\ncode = status.name\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "label = status.name\ncode = status.value\n")
        gate = GateRule(id="enum-value", language="python", rule={"pattern": "$X.value"})

        classifier = ChangeClassifier(
            SyntaxScanner(AstGrep(), {"gate:enum-value": gate}), working_tree
        )

        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        kinds = classification["a.py"].kinds
        assert kinds is not None
        assert "gate:enum-value" in kinds

    def test_change_outside_a_gate_match_does_not_touch_the_gate(
        self, git_repo, working_tree, line_scopes
    ):
        git_repo.write("a.py", "label = status.name\ncode = status.value\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "label = status.title\ncode = status.value\n")
        gate = GateRule(id="enum-value", language="python", rule={"pattern": "$X.value"})

        classifier = ChangeClassifier(
            SyntaxScanner(AstGrep(), {"gate:enum-value": gate}), working_tree
        )

        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        kinds = classification["a.py"].kinds
        assert kinds is not None
        assert "gate:enum-value" not in kinds

    def test_for_rulesets_touches_a_rulesets_gate(self, git_repo, working_tree, line_scopes):
        git_repo.write(
            "python/gates/enum-value.yml",
            "id: enum-value\nlanguage: python\nrule:\n  pattern: $X.value\n",
        )
        git_repo.write("a.py", "label = status.name\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "label = status.value\n")
        ruleset = Ruleset(name="example/python", root=git_repo.root / "python")
        classifier = ChangeClassifier.for_rulesets(AstGrep(), [ruleset], working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        kinds = classification["a.py"].kinds
        assert kinds is not None
        assert "gate:example/python/enum-value" in kinds

    def test_fixture_is_its_own_kind(self, git_repo, working_tree, line_scopes):
        git_repo.write("conftest.py", "@pytest.fixture\ndef order():\n    return Order()\n")

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        kinds = classification["conftest.py"].kinds
        assert kinds is not None
        assert ChangeKind.FIXTURE in kinds
        assert ChangeKind.HELPER_FUNCTION not in kinds
        assert ChangeKind.TEST_FUNCTION not in kinds

    def test_method_edit_judges_the_method(self, git_repo, working_tree, line_scopes):
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

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {5, 6}

    def test_class_body_edit_outside_a_method_judges_the_class_header_and_the_line(
        self, git_repo, working_tree, line_scopes
    ):
        git_repo.write(
            "a.py", "class Order:\n    rate = 1\n\n    def tax(self):\n        return 0\n"
        )
        git_repo.commit("Add a")
        git_repo.write(
            "a.py", "class Order:\n    rate = 2\n\n    def tax(self):\n        return 0\n"
        )

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {1, 2}

    def test_class_body_edit_judges_every_line_of_a_class_header(
        self, git_repo, working_tree, line_scopes
    ):
        source = (
            "class Order(\n    Base,\n):\n    def tax(self):\n        return 0\n\n    rate = 1\n"
        )
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("rate = 1", "rate = 2"))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {1, 2, 3, 7}

    def test_class_header_edit_judges_the_class(self, git_repo, working_tree, line_scopes):
        git_repo.write("a.py", "class Order:\n    def tax(self):\n        return 0\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "class Order(Base):\n    def tax(self):\n        return 0\n")

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {1, 2, 3}

    def test_module_level_edit_judges_the_changed_line(self, git_repo, working_tree, line_scopes):
        git_repo.write("a.py", "RATE = 1\n\n\ndef tax():\n    return 0\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "RATE = 2\n\n\ndef tax():\n    return 0\n")

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {1}

    def test_method_added_to_a_class_judges_the_method(self, git_repo, working_tree, line_scopes):
        git_repo.write("a.py", "class Order:\n    def total(self):\n        return 1\n")
        git_repo.commit("Add a")
        git_repo.write(
            "a.py",
            "class Order:\n    def total(self):\n        return 1\n\n"
            "    def tax(self):\n        return 0\n",
        )

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {5, 6}

    def test_new_file_judges_every_line_with_code(self, git_repo, working_tree, line_scopes):
        git_repo.write("a.py", "RATE = 2\n\n\ndef tax():\n    return 0\n")

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {1, 4, 5}

    def test_judged_lines_for_a_trigger_take_in_its_node_around_the_change(
        self, git_repo, working_tree, line_scopes
    ):
        source = "try:\n    import fast\nexcept ImportError:\n    fast = None\n"
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("fast = None", "fast = False"))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {3, 4}
        assert classification["a.py"].judged_lines(frozenset({ChangeKind.CONTROL_FLOW})) == {
            1,
            2,
            3,
            4,
        }

    def test_decorator_edit_judges_the_decorated_method(self, git_repo, working_tree, line_scopes):
        source = "class Order:\n    @property\n    def total(self):\n        return 1\n"
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("@property", "@cached_property"))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {2, 3, 4}

    def test_class_body_edit_judges_the_class_decorators_with_its_header(
        self, git_repo, working_tree, line_scopes
    ):
        source = "@dataclass\nclass Order:\n    def tax(self):\n        return 0\n\n    rate = 1\n"
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("rate = 1", "rate = 2"))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {1, 2, 6}

    def test_multi_line_statement_edit_judges_the_whole_statement(
        self, git_repo, working_tree, line_scopes
    ):
        source = "RATES = {\n    'net': 1,\n    'gross': 2,\n}\nTAX = 3\n"
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("'gross': 2", "'gross': 4"))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {1, 2, 3, 4}

    def test_multi_line_statement_edit_in_a_class_body_judges_the_header_and_statement(
        self, git_repo, working_tree, line_scopes
    ):
        source = (
            "class Order:\n    def tax(self):\n        return 0\n\n"
            "    rates = (\n        1,\n        2,\n    )\n"
        )
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("        2,", "        4,"))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {1, 5, 6, 7, 8}

    def test_removed_method_judges_the_class_header_not_the_method_before_it(
        self, git_repo, working_tree, line_scopes
    ):
        git_repo.write(
            "a.py",
            "class Order:\n    def total(self):\n        raise ValueError\n\n"
            "    def tax(self):\n        return 0\n",
        )
        git_repo.commit("Add a")
        git_repo.write("a.py", "class Order:\n    def total(self):\n        raise ValueError\n")

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        kinds = classification["a.py"].kinds
        assert classification["a.py"].judged_lines(frozenset()) == {1}
        assert kinds is not None
        assert ChangeKind.RETURN_YIELD in kinds
        assert ChangeKind.RAISE not in kinds

    def test_removed_first_member_judges_the_class_header_not_the_class(
        self, git_repo, working_tree, line_scopes
    ):
        git_repo.write(
            "a.py",
            "class Order:\n    rate = 1\n\n    def tax(self):\n        return 0\n",
        )
        git_repo.commit("Add a")
        git_repo.write("a.py", "class Order:\n\n    def tax(self):\n        return 0\n")

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {1}

    def test_removed_line_in_a_function_judges_the_function(
        self, git_repo, working_tree, line_scopes
    ):
        git_repo.write("a.py", "def tax():\n    log()\n    return 0\n\n\nRATE = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "def tax():\n    return 0\n\n\nRATE = 1\n")

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {1, 2}

    def test_removed_module_level_statement_judges_no_line_beside_it(
        self, git_repo, working_tree, line_scopes
    ):
        git_repo.write("a.py", "def tax():\n    return 0\n\n\nRATE = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "def tax():\n    return 0\n")

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == frozenset()

    def test_removed_line_of_a_multi_line_statement_judges_the_rest_of_the_statement(
        self, git_repo, working_tree, line_scopes
    ):
        git_repo.write("a.py", "TAX = 3\nRATES = (\n    1,\n    2,\n)\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "TAX = 3\nRATES = (\n    1,\n)\n")

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {2, 3, 4}

    def test_removal_judges_its_context_where_earlier_changes_moved_it(
        self, git_repo, working_tree, line_scopes
    ):
        git_repo.write("a.py", "A = 1\n\n\ndef tax():\n    log()\n    return 0\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "A = 1\nB = 2\nC = 3\n\n\ndef tax():\n    return 0\n")

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {2, 3, 6, 7}

    def test_handler_header_edit_judges_the_handler_and_the_block_it_guards(
        self, git_repo, working_tree, line_scopes
    ):
        source = (
            "try:\n    load()\nexcept KeyError:\n    pass\n"
            "except ValueError:\n    retry()\nfinally:\n    close()\n"
        )
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("except ValueError:", "except TypeError:"))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {1, 2, 5, 6}

    def test_handler_is_judged_with_its_own_try_block_not_a_nested_one(
        self, git_repo, working_tree, line_scopes
    ):
        source = (
            "try:\n    load()\nexcept KeyError:\n    try:\n        fetch()\n"
            "    except OSError:\n        pass\nexcept ValueError:\n    retry()\n"
        )
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("except ValueError:", "except TypeError:"))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {1, 2, 8, 9}

    def test_else_header_edit_judges_only_its_clause(self, git_repo, working_tree, line_scopes):
        source = "if fast:\n    run()\nelif slow:\n    wait()\nelse:\n    stop()\n"
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("elif slow:", "elif late:"))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {3, 4}

    def test_comment_edit_judges_only_the_comment(self, git_repo, working_tree, line_scopes):
        source = "def tax():\n    # net\n    return 0\n"
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("# net", "# gross"))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {2}
        assert classification["a.py"].kinds == {ChangeKind.COMMENT, ChangeKind.ANY}

    def test_removed_comment_judges_no_code(self, git_repo, working_tree, line_scopes):
        git_repo.write("a.py", "def tax():\n    # net\n    return 0\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "def tax():\n    return 0\n")

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == frozenset()
        assert classification["a.py"].kinds == {ChangeKind.COMMENT, ChangeKind.ANY}

    def test_docstring_edit_judges_only_the_docstring(self, git_repo, working_tree, line_scopes):
        source = 'def tax():\n    """Net tax."""\n    return 0\n'
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("Net", "Gross"))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {2}
        assert classification["a.py"].kinds == {ChangeKind.DOCSTRING, ChangeKind.ANY}

    def test_module_docstring_edit_touches_no_code_kind(self, git_repo, working_tree, line_scopes):
        source = '"""Pricing.\n\nRates.\n"""  # doc\nRATE = 1\n'
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("Rates.", "Tax rates."))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {3}
        assert classification["a.py"].kinds == {ChangeKind.DOCSTRING, ChangeKind.ANY}

    def test_docstring_after_a_shebang_is_a_docstring(self, git_repo, working_tree, line_scopes):
        source = '#!/usr/bin/env python\n"""Pricing.\n\nRates.\n"""\nRATE = 1\n'
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("Rates.", "Tax rates."))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {4}
        assert classification["a.py"].kinds == {ChangeKind.DOCSTRING, ChangeKind.ANY}

    def test_comment_edit_takes_in_no_trigger_node_around_it(
        self, git_repo, working_tree, line_scopes
    ):
        source = "if fast:\n    # net\n    run()\n"
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("net", "gross"))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset({ChangeKind.CONTROL_FLOW})) == {2}

    def test_removed_statement_in_a_module_level_block_judges_the_block_header(
        self, git_repo, working_tree, line_scopes
    ):
        source = "if debug:\n    log()\n    run()\nelse:\n    stop()\n"
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("    log()\n", ""))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {1}

    def test_removed_handler_judges_its_try_and_the_block_it_guarded(
        self, git_repo, working_tree, line_scopes
    ):
        source = "try:\n    load()\nexcept KeyError:\n    pass\nfinally:\n    close()\n"
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("except KeyError:\n    pass\n", ""))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {1, 2}

    def test_removal_in_a_renamed_file_judges_its_context(
        self, git_repo, working_tree, line_scopes
    ):
        source = (
            "".join(f"X{i} = {i}\n" for i in range(20)) + "def tax():\n    log()\n    return 0\n"
        )
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.git("mv", "a.py", "b.py")
        git_repo.write("b.py", source.replace("    log()\n", ""))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["b.py"].judged_lines(frozenset()) == {21, 22}
        assert ChangeKind.DEFINITION_ADDED_OR_REMOVED not in (classification["b.py"].kinds or ())

    def test_renamed_file_keeps_its_base_beside_a_new_file_at_its_old_path(
        self, git_repo, working_tree, line_scopes
    ):
        source = (
            "".join(f"X{i} = {i}\n" for i in range(20)) + "def tax():\n    log()\n    return 0\n"
        )
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.git("mv", "a.py", "0.py")
        git_repo.write("0.py", source.replace("    log()\n", ""))
        git_repo.write("a.py", "def rate():\n    return 1\n")

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["0.py"].judged_lines(frozenset()) == {21, 22}
        assert ChangeKind.DEFINITION_ADDED_OR_REMOVED not in (classification["0.py"].kinds or ())

    def test_removed_one_line_handler_judges_its_try_and_the_block_it_guarded(
        self, git_repo, working_tree, line_scopes
    ):
        source = "try:\n    load()\n    run()\nexcept KeyError: pass\nclose()\n"
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("except KeyError: pass\n", ""))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {1, 2, 3}

    def test_removed_function_in_a_module_level_block_judges_the_block_header(
        self, git_repo, working_tree, line_scopes
    ):
        source = "if typing:\n    def f():\n        load()\n    rate = 1\n"
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("    def f():\n        load()\n", ""))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {1}

    def test_class_body_edit_no_statement_holds_judges_the_class_header_and_the_line(
        self, git_repo, working_tree, line_scopes
    ):
        source = "class A:\n    x = 1\n    y = 2\n\n    def g(self):\n        pass\n"
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("    y = 2\n", "    y =\n"))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification["a.py"].judged_lines(frozenset()) == {1, 3}

    def test_file_without_change_kinds_judges_its_changed_points(
        self, git_repo, working_tree, line_scopes, make_file_classification
    ):
        git_repo.write("a.md", "one\ntwo\nthree\nfour\nfive\n")
        git_repo.commit("Add a")
        git_repo.write("a.md", "ONE\ntwo\nthree\nfive\n")

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification == {
            "a.md": make_file_classification(kinds=None, judged=frozenset({1, 3}))
        }
