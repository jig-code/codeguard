from rules_package import PLACEMENT_RULE

from codeguard.config import RulesetLoader
from codeguard.rule_validation.judge_rule_file import JudgeRuleFile
from codeguard.rule_validation.rule_file_outline import RuleFileOutline

BINDING = 'paths: ["**/*.py"]\ntriggers: [any]\n'


class TestJudgeRuleFile:
    def test_rule_files_are_ordered_by_rule_id(self, directory):
        directory.write(".codeguard/rules/judge/zebra.md", PLACEMENT_RULE)
        directory.write(".codeguard/rules/judge/apple.md", PLACEMENT_RULE)
        directory.write(".codeguard/bindings/a.yaml", f"rule: zebra\n{BINDING}")
        directory.write(".codeguard/bindings/b.yaml", f"rule: apple\n{BINDING}")

        rule_files = JudgeRuleFile.from_ruleset(RulesetLoader.local(directory.root).load())

        assert rule_files == (
            JudgeRuleFile(
                "apple", is_legacy_skill=False, outline=RuleFileOutline.from_text(PLACEMENT_RULE)
            ),
            JudgeRuleFile(
                "zebra", is_legacy_skill=False, outline=RuleFileOutline.from_text(PLACEMENT_RULE)
            ),
        )

    def test_rule_bound_with_the_skill_key_is_a_legacy_skill(self, directory):
        directory.write("skills/placement/SKILL.md", PLACEMENT_RULE)
        directory.write(".codeguard/bindings/placement.yaml", f"skill: skills/placement\n{BINDING}")

        rule_files = JudgeRuleFile.from_ruleset(RulesetLoader.local(directory.root).load())

        assert rule_files == (
            JudgeRuleFile(
                "placement", is_legacy_skill=True, outline=RuleFileOutline.from_text(PLACEMENT_RULE)
            ),
        )
