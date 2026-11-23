import yaml

from codeguard.ast_grep import AstGrep
from codeguard.config import Config, RulesetLoader
from codeguard.project import Project, ProjectValidations
from codeguard.repository import WorkingTree
from codeguard.rule_validation import ValidationResult


class TestProjectValidations:
    def test_each_ruleset_is_validated(self, directory, make_judge_rule):
        for ruleset in ("python", "ruby"):
            directory.write(f"{ruleset}/rules/judge/{ruleset}-rule.md", make_judge_rule().text)
            directory.write(
                f"{ruleset}/bindings/{ruleset}-rule.yaml",
                yaml.safe_dump({"rule": f"{ruleset}-rule", "paths": ["**"], "triggers": ["any"]}),
            )
        project = Project(WorkingTree.at(directory.root), Config(), AstGrep())
        loaders = [
            RulesetLoader(repo=directory.root, root=directory.root / ruleset, name=ruleset)
            for ruleset in ("python", "ruby")
        ]

        result = ProjectValidations(project, loaders).validations().run()

        assert result == ValidationResult(
            warnings=(
                "python-rule: broad triggers any; a gate on the code its violations need skips "
                "more files",
                "ruby-rule: broad triggers any; a gate on the code its violations need skips more "
                "files",
            )
        )
