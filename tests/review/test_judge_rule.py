import pytest


class TestJudgeRule:
    @pytest.mark.parametrize(
        "suffix",
        ["", "\n## Why\n\n", "\n## Why\n## Examples\n\nship(Status.SHIPPED)\n"],
        ids=["no-section", "empty-section", "section-without-text"],
    )
    def test_rule_without_a_why_text_does_not_say_why(self, make_judge_rule, suffix):
        rule = make_judge_rule(text="# Placement\n\nA method lives on the type it reads." + suffix)

        assert not rule.says_why

    def test_rule_with_a_why_section_says_why(self, make_judge_rule):
        rule = make_judge_rule(
            text="# Placement\n\nA method lives on its type.\n\n## Why\n\nIt stays with its data.\n"
        )

        assert rule.says_why

    def test_why_section_may_end_in_a_source(self, make_judge_rule):
        text = make_judge_rule().text + "\nSource: https://example.com/style-guide#placement\n"

        assert make_judge_rule(text=text).says_why
