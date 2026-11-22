import yaml
from rules_package import PLACEMENT_RULE

from codeguard.config import RulesetLoader
from codeguard.rule_validation.judge_rule_file import JudgeRuleFile
from codeguard.rule_validation.rule_file_outline import RuleFileOutline

BINDING = {"paths": ["**/*.py"], "triggers": ["any"]}


class TestJudgeRuleFile:
    def test_rule_files_are_ordered_by_rule_id(self, directory):
        directory.write(".codeguard/rules/judge/zebra.md", PLACEMENT_RULE)
        directory.write(".codeguard/rules/judge/apple.md", PLACEMENT_RULE)
        directory.write(".codeguard/bindings/a.yaml", yaml.safe_dump({"rule": "zebra"} | BINDING))
        directory.write(".codeguard/bindings/b.yaml", yaml.safe_dump({"rule": "apple"} | BINDING))

        rule_files = JudgeRuleFile.from_ruleset(RulesetLoader.local(directory.root).load())

        assert rule_files == (
            JudgeRuleFile(
                "apple", is_legacy_skill=False, outline=RuleFileOutline.from_text(PLACEMENT_RULE)
            ),
            JudgeRuleFile(
                "zebra", is_legacy_skill=False, outline=RuleFileOutline.from_text(PLACEMENT_RULE)
            ),
        )

    def test_legacy_skill_binding_is_marked_legacy(self, directory):
        directory.write("skills/placement/SKILL.md", f"---\nname: placement\n---\n{PLACEMENT_RULE}")
        directory.write(
            ".codeguard/bindings/placement.yaml",
            yaml.safe_dump({"skill": "skills/placement"} | BINDING),
        )

        rule_files = JudgeRuleFile.from_ruleset(RulesetLoader.local(directory.root).load())

        assert rule_files == (
            JudgeRuleFile(
                "placement", is_legacy_skill=True, outline=RuleFileOutline.from_text(PLACEMENT_RULE)
            ),
        )
