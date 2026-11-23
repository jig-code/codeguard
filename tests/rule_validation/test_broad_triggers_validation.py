import yaml

from codeguard.config import RulesetLoader
from codeguard.rule_validation import BroadTriggersValidation, ValidationResult


class TestBroadTriggersValidation:
    def test_each_broad_trigger_of_a_binding_is_a_warning(self, directory, make_judge_rule):
        directory.write(".codeguard/rules/judge/placement.md", make_judge_rule().text)
        directory.write(
            ".codeguard/bindings/placement.yaml",
            yaml.safe_dump(
                {"rule": "placement", "paths": ["**/*.py"], "triggers": ["code", "any", "fixture"]}
            ),
        )

        result = BroadTriggersValidation(RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult(
            warnings=(
                "placement: broad triggers any, code; "
                "a gate on the code its violations need skips more files",
            )
        )

    def test_binding_with_only_narrow_triggers_passes(self, directory, make_judge_rule):
        directory.write(".codeguard/rules/judge/placement.md", make_judge_rule().text)
        directory.write(
            ".codeguard/bindings/placement.yaml",
            yaml.safe_dump({"rule": "placement", "paths": ["**/*.py"], "triggers": ["fixture"]}),
        )

        result = BroadTriggersValidation(RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult()

    def test_bindings_that_do_not_load_are_a_warning_that_triggers_were_not_checked(
        self, directory
    ):
        directory.write(".codeguard/bindings/broken.yaml", yaml.safe_dump({"path": ["a.py"]}))

        result = BroadTriggersValidation(RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult(
            warnings=(
                f"triggers not checked: {directory.root}/.codeguard is invalid:\n"
                "  bindings.broken.yaml.paths: Field required\n"
                "  bindings.broken.yaml.path: Extra inputs are not permitted",
            )
        )
