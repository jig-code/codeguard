import textwrap

from codeguard.ast_grep import AstGrep
from codeguard.config import ChangeKind, GateRule, Ruleset
from codeguard.syntax import ChangeClassifier, Classification, SyntaxScanner


class TestChangeClassifier:
    def test_trailing_comment_edit_touches_every_kind_on_its_line(
        self, git_repo, working_tree, line_scopes
    ):
        git_repo.write("a.py", "class Order:\n    total = 1  # net\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "class Order:\n    total = 1  # gross\n")

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification.touched_kinds("a.py") == {
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

        assert classification.touched_kinds("a.py") == {ChangeKind.COMMENT, ChangeKind.ANY}

    def test_body_only_edit_does_not_touch_the_class_header(
        self, git_repo, working_tree, line_scopes
    ):
        git_repo.write("a.py", "class Order(Base):\n    def total(self):\n        return 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", "class Order(Base):\n    def total(self):\n        return 2\n")

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        kinds = classification.touched_kinds("a.py")
        assert kinds is not None
        assert ChangeKind.FUNCTION_BODY in kinds
        assert ChangeKind.CLASS_HEADER not in kinds

    def test_new_file_touches_the_kinds_it_contains_and_no_others(
        self, git_repo, working_tree, line_scopes
    ):
        git_repo.write("test_a.py", "def test_total():\n    assert total() == 1\n")

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification.touched_kinds("test_a.py") == {
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

        kinds = classification.touched_kinds("a.py")
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

        kinds = classification.touched_kinds("a.py")
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

        kinds = classification.touched_kinds("a.py")
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

        kinds = classification.touched_kinds("a.py")
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

        kinds = classification.touched_kinds("a.py")
        assert kinds is not None
        assert "gate:example/python/enum-value" in kinds

    def test_fixture_is_its_own_kind(self, git_repo, working_tree, line_scopes):
        git_repo.write("conftest.py", "@pytest.fixture\ndef order():\n    return Order()\n")

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        kinds = classification.touched_kinds("conftest.py")
        assert kinds is not None
        assert ChangeKind.FIXTURE in kinds
        assert ChangeKind.HELPER_FUNCTION not in kinds
        assert ChangeKind.TEST_FUNCTION not in kinds

    def test_method_edit_takes_in_the_method(self, git_repo, working_tree, line_scopes):
        source = textwrap.dedent("""\
            class Order:
                def total(self):
                    return 1

                def tax(self):
                    return 0
        """)
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("return 0", "return 2"))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification.context_lines("a.py") == {5, 6}

    def test_edit_in_a_nested_function_takes_in_only_the_nested_function(
        self, git_repo, working_tree, line_scopes
    ):
        source = textwrap.dedent("""\
            def outer():
                def inner():
                    return 1

                return inner
        """)
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("return 1", "return 2"))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification.context_lines("a.py") == {2, 3}

    def test_class_body_edit_outside_a_method_takes_in_the_class(
        self, git_repo, working_tree, line_scopes
    ):
        source = textwrap.dedent("""\
            class Order:
                rate = 1

                def tax(self):
                    return 0
        """)
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("rate = 1", "rate = 2"))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification.context_lines("a.py") == {1, 2, 3, 4, 5}

    def test_class_header_edit_takes_in_the_class(self, git_repo, working_tree, line_scopes):
        source = textwrap.dedent("""\
            class Order:
                def tax(self):
                    return 0
        """)
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("class Order:", "class Order(Base):"))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification.context_lines("a.py") == {1, 2, 3}

    def test_decorator_edit_takes_in_the_decorated_method(
        self, git_repo, working_tree, line_scopes
    ):
        source = textwrap.dedent("""\
            class Order:
                @property
                def total(self):
                    return 1
        """)
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("@property", "@cached_property"))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification.context_lines("a.py") == {2, 3, 4}

    def test_module_level_edit_takes_in_no_scope(self, git_repo, working_tree, line_scopes):
        source = textwrap.dedent("""\
            RATE = 1


            def tax():
                return 0
        """)
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("RATE = 1", "RATE = 2"))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification.context_lines("a.py") == frozenset()

    def test_method_added_to_a_class_takes_in_the_method(self, git_repo, working_tree, line_scopes):
        git_repo.write(
            "a.py",
            textwrap.dedent("""\
                class Order:
                    def total(self):
                        return 1
            """),
        )
        git_repo.commit("Add a")
        git_repo.write(
            "a.py",
            textwrap.dedent("""\
                class Order:
                    def total(self):
                        return 1

                    def tax(self):
                        return 0
            """),
        )

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification.context_lines("a.py") == {5, 6}

    def test_new_file_takes_in_each_scope(self, git_repo, working_tree, line_scopes):
        git_repo.write(
            "a.py",
            textwrap.dedent("""\
                RATE = 2


                def tax():
                    return 0
            """),
        )

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification.context_lines("a.py") == {4, 5}

    def test_comment_edit_takes_in_the_function_around_it(
        self, git_repo, working_tree, line_scopes
    ):
        source = textwrap.dedent("""\
            def tax():
                # net
                return 0
        """)
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("# net", "# gross"))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification.context_lines("a.py") == {1, 2, 3}
        assert classification.touched_kinds("a.py") == {ChangeKind.COMMENT, ChangeKind.ANY}

    def test_docstring_edit_touches_only_the_docstring_kind(
        self, git_repo, working_tree, line_scopes
    ):
        source = textwrap.dedent('''\
            def tax():
                """Net tax."""
                return 0
        ''')
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("Net", "Gross"))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification.touched_kinds("a.py") == {ChangeKind.DOCSTRING, ChangeKind.ANY}

    def test_module_docstring_edit_touches_no_code_kind(self, git_repo, working_tree, line_scopes):
        source = textwrap.dedent('''\
            """Pricing.

            Rates.
            """  # doc
            RATE = 1
        ''')
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("Rates.", "Tax rates."))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification.touched_kinds("a.py") == {ChangeKind.DOCSTRING, ChangeKind.ANY}

    def test_docstring_after_a_shebang_is_a_docstring(self, git_repo, working_tree, line_scopes):
        source = textwrap.dedent('''\
            #!/usr/bin/env python
            """Pricing.

            Rates.
            """
            RATE = 1
        ''')
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("Rates.", "Tax rates."))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification.touched_kinds("a.py") == {ChangeKind.DOCSTRING, ChangeKind.ANY}

    def test_removed_line_in_a_function_takes_in_the_rest_of_the_function(
        self, git_repo, working_tree, line_scopes
    ):
        source = textwrap.dedent("""\
            def tax():
                log()
                return 0


            RATE = 1
        """)
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("    log()\n", ""))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification.context_lines("a.py") == {1, 2}

    def test_removed_comment_takes_in_the_rest_of_the_function(
        self, git_repo, working_tree, line_scopes
    ):
        source = textwrap.dedent("""\
            def tax():
                # net
                return 0
        """)
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.write("a.py", source.replace("    # net\n", ""))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification.context_lines("a.py") == {1, 2}
        assert classification.touched_kinds("a.py") == {ChangeKind.COMMENT, ChangeKind.ANY}

    def test_removed_method_takes_in_no_kept_line_and_touches_its_kinds(
        self, git_repo, working_tree, line_scopes
    ):
        git_repo.write(
            "a.py",
            textwrap.dedent("""\
                class Order:
                    def total(self):
                        raise ValueError

                    def tax(self):
                        return 0
            """),
        )
        git_repo.commit("Add a")
        git_repo.write(
            "a.py",
            textwrap.dedent("""\
                class Order:
                    def total(self):
                        raise ValueError
            """),
        )

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        kinds = classification.touched_kinds("a.py")
        assert classification.context_lines("a.py") == frozenset()
        assert kinds is not None
        assert ChangeKind.RETURN_YIELD in kinds
        assert ChangeKind.RAISE not in kinds

    def test_removed_module_level_statement_takes_in_no_scope(
        self, git_repo, working_tree, line_scopes
    ):
        function = textwrap.dedent("""\
            def tax():
                return 0
        """)
        git_repo.write("a.py", function + "\n\nRATE = 1\n")
        git_repo.commit("Add a")
        git_repo.write("a.py", function)

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification.context_lines("a.py") == frozenset()

    def test_removal_takes_in_its_function_where_earlier_changes_moved_it(
        self, git_repo, working_tree, line_scopes
    ):
        git_repo.write(
            "a.py",
            textwrap.dedent("""\
                A = 1


                def tax():
                    log()
                    return 0
            """),
        )
        git_repo.commit("Add a")
        git_repo.write(
            "a.py",
            textwrap.dedent("""\
                A = 1
                B = 2
                C = 3


                def tax():
                    return 0
            """),
        )

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification.context_lines("a.py") == {6, 7}

    def test_removal_in_a_renamed_file_takes_in_its_function(
        self, git_repo, working_tree, line_scopes
    ):
        source = "".join(f"X{i} = {i}\n" for i in range(20)) + textwrap.dedent("""\
            def tax():
                log()
                return 0
        """)
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.git("mv", "a.py", "b.py")
        git_repo.write("b.py", source.replace("    log()\n", ""))

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification.context_lines("b.py") == {21, 22}
        assert ChangeKind.DEFINITION_ADDED_OR_REMOVED not in (
            classification.touched_kinds("b.py") or ()
        )

    def test_renamed_file_keeps_its_base_beside_a_new_file_at_its_old_path(
        self, git_repo, working_tree, line_scopes
    ):
        source = "".join(f"X{i} = {i}\n" for i in range(20)) + textwrap.dedent("""\
            def tax():
                log()
                return 0
        """)
        git_repo.write("a.py", source)
        git_repo.commit("Add a")
        git_repo.git("mv", "a.py", "0.py")
        git_repo.write("0.py", source.replace("    log()\n", ""))
        git_repo.write(
            "a.py",
            textwrap.dedent("""\
                def rate():
                    return 1
            """),
        )

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification.context_lines("0.py") == {21, 22}
        assert ChangeKind.DEFINITION_ADDED_OR_REMOVED not in (
            classification.touched_kinds("0.py") or ()
        )

    def test_file_without_a_syntax_table_takes_in_no_context(
        self, git_repo, working_tree, line_scopes, make_file_classification
    ):
        git_repo.write("a.md", "one\ntwo\nthree\nfour\nfive\n")
        git_repo.commit("Add a")
        git_repo.write("a.md", "ONE\ntwo\nthree\nfive\n")

        classifier = ChangeClassifier(SyntaxScanner(AstGrep(), {}), working_tree)
        classification = classifier.classify(line_scopes.changed_lines("HEAD"))

        assert classification == Classification(
            {"a.md": make_file_classification(touched_kinds=None, context_lines=frozenset())}
        )
