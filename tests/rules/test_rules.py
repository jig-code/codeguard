from importlib import metadata

import pytest
import yaml
from packaging.version import Version

from codeguard.ast_grep import AstGrep
from codeguard.config import ConfigError
from codeguard.repository import LineScopes, WorkingTree
from codeguard.review import JudgePlan, PlannedCall
from codeguard.rules import Rules

pytestmark = pytest.mark.usefixtures("judgement_cache")

GEMINI_PLACEMENT_BINDING = {
    "rule": "placement",
    "triggers": ["any"],
    "provider": "gemini",
    "model": "gemini-judge-test",
}


class TestRules:
    def test_review_needs_each_binding_s_sign_in_even_when_no_file_matches_it(
        self, repo, make_judge_rule
    ):
        repo.write(".codeguard/rules/judge/placement.md", make_judge_rule().text)
        repo.write(
            ".codeguard/bindings/placement.yaml",
            yaml.safe_dump({**GEMINI_PLACEMENT_BINDING, "paths": ["**/*.rb"]}),
        )
        repo.commit("Bind the rule")
        repo.write("a.py", "x = 1\n")
        working_tree = WorkingTree.at(repo.root)
        scope = LineScopes.at(working_tree).changed_lines("HEAD")

        with pytest.raises(ConfigError) as error:
            Rules(working_tree).review(scope)

        assert str(error.value) == "Gemini needs a project: set CODEGUARD_JUDGE__GEMINI__PROJECT"

    def test_plan_lists_a_gemini_judge_call_without_a_gemini_sign_in(self, repo, make_judge_rule):
        repo.write(".codeguard/rules/judge/placement.md", make_judge_rule().text)
        repo.write(
            ".codeguard/bindings/placement.yaml",
            yaml.safe_dump({**GEMINI_PLACEMENT_BINDING, "paths": ["**/*.py"]}),
        )
        repo.commit("Bind the rule")
        repo.write("a.py", "x = 1\n")
        working_tree = WorkingTree.at(repo.root)
        scope = LineScopes.at(working_tree).changed_lines("HEAD")

        plan = Rules(working_tree).plan(scope)

        assert plan == JudgePlan(
            calls=(PlannedCall(rule="placement", file="a.py", cached=False, triggered=True),)
        )

    def test_ast_grep_is_the_version_the_config_pins(self, repo):
        bundled = metadata.version("ast-grep-cli")
        repo.write(".codeguard/config.yaml", yaml.safe_dump({"ast-grep": bundled}))

        ast_grep = Rules(WorkingTree.at(repo.root)).ast_grep

        assert ast_grep == AstGrep(Version(bundled))
