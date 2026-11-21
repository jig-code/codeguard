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

    def test_why_text_may_sit_under_a_subheading(self, make_judge_rule):
        rule = make_judge_rule(
            text="# Placement\n\nA method lives on its type.\n\n## Why\n\n### Cost\n\nIt costs.\n"
        )

        assert rule.says_why

    def test_why_section_may_end_in_a_source(self, make_judge_rule):
        rule = make_judge_rule(
            text="# Placement\n\nA method lives on its type.\n\n## Why\n\nIt stays with its data.\n"
            "\nSource: https://example.com/style-guide#placement\n"
        )

        assert rule.says_why

    def test_title_statement_and_why_have_no_format_problems(self, make_judge_rule):
        assert make_judge_rule().format_problems() == ()

    @pytest.mark.parametrize(
        "text",
        [
            "A name says what it holds.\n",
            "---\nname: naming\n---\n\n# Naming\n\nA name says what it holds.\n",
            "",
        ],
        ids=["no-title", "frontmatter", "empty-file"],
    )
    def test_text_that_does_not_start_with_a_title_has_only_that_problem(
        self, make_judge_rule, text
    ):
        rule = make_judge_rule(text=text)

        assert rule.format_problems() == ("must start with a `# ` title",)

    def test_title_with_no_statement_has_that_problem(self, make_judge_rule):
        rule = make_judge_rule(text="# Naming\n\n## Why\n\nNames are read more than written.\n")

        assert rule.format_problems() == ("has no statement under its title",)

    @pytest.mark.parametrize(
        "suffix",
        ["", "\n## Why\n"],
        ids=["no-why-heading", "empty-why"],
    )
    def test_rule_without_a_why_text_has_that_problem(self, make_judge_rule, suffix):
        rule = make_judge_rule(text="# Naming\n\nA name says what it holds.\n" + suffix)

        assert rule.format_problems() == ("has no `## Why` section with text",)

    def test_section_other_than_why_is_a_problem(self, make_judge_rule):
        rule = make_judge_rule(
            text="# Naming\n\nA name says what it holds.\n\n## Forms\n\nA list.\n\n"
            "## Why\n\nNames are read more than written.\n"
        )

        assert rule.format_problems() == (
            "has the heading '## Forms', but holds only a title, the statement and `## Why`",
        )

    def test_comment_in_a_code_fence_is_not_a_heading(self, make_judge_rule):
        rule = make_judge_rule(
            text="# Naming\n\nA name says what it holds, as in:\n\n```\n# note\n```\n\n"
            "## Why\n\nNames are read more than written.\n"
        )

        assert rule.format_problems() == ()
