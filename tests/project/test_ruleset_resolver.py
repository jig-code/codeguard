from dataclasses import replace
from importlib import metadata

import pytest
import yaml
from rules_package import write_package

from codeguard.ast_grep import AstGrep
from codeguard.config import Config, ConfigError, RulesetLoader
from codeguard.project import RulesetResolver


class TestOwnRulesets:
    def test_package_repo_owns_its_local_ruleset_and_each_ruleset_its_manifest_lists(
        self, directory
    ):
        write_package(directory)

        own = RulesetResolver(directory.root, Config(), AstGrep()).own_rulesets

        assert own == [
            RulesetLoader.local(directory.root),
            RulesetLoader(
                repo=directory.root, root=directory.root / "python", name="example/python"
            ),
        ]

    def test_package_repo_outside_its_ast_grep_range_is_an_error(self, directory):
        write_package(directory)
        directory.write(
            "codeguard-package.yaml",
            yaml.safe_dump({"name": "example", "rulesets": ["python"], "ast-grep": "<0.45"}),
        )

        with pytest.raises(ConfigError) as error:
            _ = RulesetResolver(directory.root, Config(), AstGrep()).own_rulesets

        assert str(error.value) == (
            f"{directory.root}/codeguard-package.yaml is invalid:\n"
            f"  example supports ast-grep <0.45, not {metadata.version('ast-grep-cli')}"
        )


class TestRulesets:
    def test_skip_ci_only_reaches_every_ruleset(self, directory):
        directory.write(".codeguard/config.yaml", yaml.safe_dump({}))

        rulesets = RulesetResolver(directory.root, Config(), AstGrep(), skip_ci_only=True).rulesets

        assert rulesets == (replace(RulesetLoader.local(directory.root).load(), skip_ci_only=True),)
