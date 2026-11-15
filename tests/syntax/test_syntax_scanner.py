from codeguard.ast_grep import AstGrep
from codeguard.config import GateRule, Ruleset
from codeguard.syntax import NodeKind, SyntaxNode, SyntaxScanner

ENUM_VALUE_GATE = "id: enum-value\nlanguage: python\nrule:\n  pattern: $X.value\n"
MOCK_USE_GATE = "id: mock-use\nlanguage: python\nrule:\n  pattern: Mock()\n"


class TestSyntaxScanner:
    def test_scan_finds_each_node_kind(self, tmp_path):
        (tmp_path / "order.py").write_text("import os  # system\ntotal = os.sep\n")

        [(file, parsed)] = SyntaxScanner(AstGrep()).scan(tmp_path).items()

        node_kinds = {node for node in parsed.nodes if isinstance(node.kind, NodeKind)}

        assert (file, parsed.content, node_kinds) == (
            "order.py",
            b"import os  # system\ntotal = os.sep\n",
            {
                SyntaxNode(NodeKind.COMMENT, 11, 19, "# system", start_line=1, end_line=1),
                SyntaxNode(NodeKind.IMPORT, 0, 9, "import os", start_line=1, end_line=1),
                SyntaxNode(NodeKind.NAME, 20, 25, "total", start_line=2, end_line=2),
                SyntaxNode(NodeKind.NAME, 28, 30, "os", start_line=2, end_line=2),
                SyntaxNode(NodeKind.NAME, 31, 34, "sep", start_line=2, end_line=2),
                SyntaxNode(NodeKind.DEFINITION, 20, 25, "total", start_line=2, end_line=2),
            },
        )

    def test_scope_nodes_span_their_lines(self, tmp_path):
        (tmp_path / "order.py").write_text("class Order:\n    def total(self):\n        return 1\n")

        [parsed] = SyntaxScanner(AstGrep()).scan(tmp_path).values()

        assert [(node.start_line, node.end_line) for node in parsed.of_kind(NodeKind.SCOPE)] == [
            (1, 3),
            (2, 3),
        ]

    def test_scan_skips_files_in_unsupported_languages(self, tmp_path):
        (tmp_path / "order.rb").write_text("total = 1\n")

        assert SyntaxScanner(AstGrep()).scan(tmp_path) == {}

    def test_for_rulesets_has_each_rulesets_gates_by_qualified_name(self, tmp_path):
        local = tmp_path / ".codeguard"
        package = tmp_path / "python"
        (local / "gates").mkdir(parents=True)
        (package / "gates").mkdir(parents=True)
        (local / "gates/enum-value.yml").write_text(ENUM_VALUE_GATE)
        (package / "gates/mock-use.yml").write_text(MOCK_USE_GATE)

        scanner = SyntaxScanner.for_rulesets(
            AstGrep(),
            [Ruleset(name=None, root=local), Ruleset(name="example/python", root=package)],
        )

        assert scanner.gates == {
            "gate:enum-value": GateRule(
                id="enum-value", language="python", rule={"pattern": "$X.value"}
            ),
            "gate:example/python/mock-use": GateRule(
                id="mock-use", language="python", rule={"pattern": "Mock()"}
            ),
        }
