from codeguard.config import RulesetStructure


def make_dirs(root, *paths: str) -> None:
    for path in paths:
        (root / path).mkdir(parents=True)


class TestRulesetStructure:
    def test_ruleset_layout_has_no_problems(self, tmp_path):
        make_dirs(
            tmp_path,
            "rules/pattern",
            "gates",
            "pattern-cases/__snapshots__",
            "rule-evals",
            "bindings",
            "rules/judge",
            "skills",
        )
        (tmp_path / "pattern-cases/no-print-cases.yml").write_text("id: no-print\n")

        assert RulesetStructure(tmp_path).problems() == []

    def test_legacy_rule_tests_directory_has_no_problems(self, tmp_path):
        make_dirs(tmp_path, "rules/pattern", "rule-tests/__snapshots__")
        (tmp_path / "rule-tests/no-print-test.yml").write_text("id: no-print\n")

        assert RulesetStructure(tmp_path).problems() == []

    def test_legacy_pattern_rule_tests_directory_has_no_problems(self, tmp_path):
        make_dirs(tmp_path, "rules/pattern", "rule-tests/pattern/__snapshots__")

        assert RulesetStructure(tmp_path).problems() == []

    def test_rule_test_subdirectory_is_unexpected(self, tmp_path):
        make_dirs(tmp_path, "pattern-cases/gates", "pattern-cases/triggers")

        assert RulesetStructure(tmp_path).problems() == [
            "unexpected pattern-cases/gates",
            "unexpected pattern-cases/triggers",
        ]

    def test_unknown_directory_is_unexpected(self, tmp_path):
        make_dirs(tmp_path, "rules/pattern", "checks")

        assert RulesetStructure(tmp_path).problems() == ["unexpected checks"]

    def test_unknown_rule_kind_is_unexpected(self, tmp_path):
        make_dirs(tmp_path, "rules/pattern", "rules/semgrep", "pattern-cases/judge")

        assert RulesetStructure(tmp_path).problems() == [
            "unexpected pattern-cases/judge",
            "unexpected rules/semgrep",
        ]

    def test_rule_outside_its_kind_directory_is_unexpected(self, tmp_path):
        make_dirs(tmp_path, "rules/pattern")
        (tmp_path / "rules/no-print.yml").write_text("id: no-print\n")

        assert RulesetStructure(tmp_path).problems() == ["unexpected rules/no-print.yml"]

    def test_file_is_unexpected_unless_allowed(self, tmp_path):
        (tmp_path / "config.yaml").write_text("{}\n")

        assert RulesetStructure(tmp_path).problems() == ["unexpected config.yaml"]
        assert RulesetStructure(tmp_path, frozenset({"config.yaml"})).problems() == []

    def test_hidden_entries_are_ignored(self, tmp_path):
        (tmp_path / ".DS_Store").write_text("")
        make_dirs(tmp_path, "rules/.cache")

        assert RulesetStructure(tmp_path).problems() == []

    def test_missing_ruleset_has_no_problems(self, tmp_path):
        assert RulesetStructure(tmp_path / "missing").problems() == []
