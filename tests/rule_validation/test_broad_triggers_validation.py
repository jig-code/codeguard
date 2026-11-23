import yaml

from codeguard.config import RulesetLoader
from codeguard.rule_validation import BroadTriggersValidation, ValidationResult
from codeguard.rule_validation.broad_triggers_validation import BroadTriggers


class TestBroadTriggers:
    def test_each_broad_trigger_of_a_binding_is_named_in_its_warning(self, make_binding_config):
        binding = make_binding_config(
            rule="placement", triggers=frozenset({"code", "any", "fixture"})
        )

        assert BroadTriggers([binding]).warnings() == (
            "placement: broad triggers any, code; "
            "a gate on the code its violations need skips more files",
        )

    def test_binding_with_only_narrow_triggers_has_no_warning(self, make_binding_config):
        binding = make_binding_config(triggers=frozenset({"fixture"}))

        assert BroadTriggers([binding]).warnings() == ()

    def test_warnings_are_ordered_by_rule(self, make_binding_config):
        bindings = [
            make_binding_config(rule="zebra", triggers=frozenset({"any"})),
            make_binding_config(rule="apple", triggers=frozenset({"function-body"})),
        ]

        assert BroadTriggers(bindings).warnings() == (
            "apple: broad triggers function-body; "
            "a gate on the code its violations need skips more files",
            "zebra: broad triggers any; a gate on the code its violations need skips more files",
        )


class TestBroadTriggersValidation:
    def test_ruleset_bindings_with_broad_triggers_are_warnings(self, directory, make_judge_rule):
        directory.write(".codeguard/rules/judge/placement.md", make_judge_rule().text)
        directory.write(
            ".codeguard/bindings/placement.yaml",
            yaml.safe_dump({"rule": "placement", "paths": ["**/*.py"], "triggers": ["any"]}),
        )

        result = BroadTriggersValidation(RulesetLoader.local(directory.root)).run()

        assert result == ValidationResult(
            warnings=(
                "placement: broad triggers any; "
                "a gate on the code its violations need skips more files",
            )
        )

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
