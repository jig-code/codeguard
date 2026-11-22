from packaging.version import Version

from codeguard.packages.manifest import Manifest


class TestManifest:
    def test_ast_grep_inside_the_range_is_no_problem(self):
        manifest = Manifest.model_validate(
            {"name": "example", "rulesets": ["python"], "ast-grep": ">=0.45,<0.46"}
        )

        assert manifest.ast_grep_problem(Version("0.45.3")) is None

    def test_codeguard_outside_the_range_is_a_problem(self):
        manifest = Manifest.model_validate(
            {"name": "example", "rulesets": ["python"], "codeguard": ">=0.3"}
        )

        assert manifest.codeguard_problem(Version("0.2.0")) == (
            "example needs codeguard >=0.3, not 0.2.0; upgrade codeguard"
        )

    def test_codeguard_inside_the_range_is_no_problem(self):
        manifest = Manifest.model_validate(
            {"name": "example", "rulesets": ["python"], "codeguard": ">=0.2"}
        )

        assert manifest.codeguard_problem(Version("0.2.0")) is None
