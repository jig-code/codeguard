import pytest
from rules_package import PLACEMENT_RULE

from codeguard.rule_validation.rule_file_outline import RuleFileOutline


class TestRuleFileOutline:
    @pytest.mark.parametrize(
        "suffix",
        ["", "\n## Why\n\n", "\n## Why\n## Examples\n\nship(Status.SHIPPED)\n"],
        ids=["no-section", "empty-section", "section-without-text"],
    )
    def test_rule_without_a_why_text_does_not_say_why(self, suffix):
        outline = RuleFileOutline.from_text("# Placement\n\nA method lives on its type." + suffix)

        assert not outline.says_why

    def test_rule_with_a_why_section_says_why(self):
        assert RuleFileOutline.from_text(PLACEMENT_RULE).says_why

    def test_why_text_may_sit_under_a_subheading(self):
        outline = RuleFileOutline.from_text(
            "# Placement\n\nA method lives on its type.\n\n## Why\n\n### Cost\n\nIt costs.\n"
        )

        assert outline.says_why

    def test_why_section_may_end_in_a_source(self):
        outline = RuleFileOutline.from_text(
            "# Placement\n\nA method lives on its type.\n\n## Why\n\nIt stays with its data.\n"
            "\nSource: https://example.com/style-guide#placement\n"
        )

        assert outline.says_why

    def test_title_statement_and_why_have_no_format_problems(self):
        assert RuleFileOutline.from_text(PLACEMENT_RULE).format_problems() == ()

    @pytest.mark.parametrize(
        "text",
        [
            "A name says what it holds.\n",
            "---\nname: naming\n---\n\n# Naming\n\nA name says what it holds.\n",
            "",
        ],
        ids=["no-title", "frontmatter", "empty-file"],
    )
    def test_text_that_does_not_start_with_a_title_has_only_that_problem(self, text):
        outline = RuleFileOutline.from_text(text)

        assert outline.format_problems() == ("must start with a `# ` title",)

    def test_title_with_no_statement_has_that_problem(self):
        outline = RuleFileOutline.from_text(
            "# Naming\n\n## Why\n\nNames are read more than written.\n"
        )

        assert outline.format_problems() == ("has no statement under its title",)

    @pytest.mark.parametrize(
        "suffix",
        ["", "\n## Why\n"],
        ids=["no-why-heading", "empty-why"],
    )
    def test_rule_without_a_why_text_has_that_problem(self, suffix):
        outline = RuleFileOutline.from_text("# Naming\n\nA name says what it holds.\n" + suffix)

        assert outline.format_problems() == ("has no `## Why` section with text",)

    def test_section_other_than_why_is_a_problem(self):
        outline = RuleFileOutline.from_text(
            "# Naming\n\nA name says what it holds.\n\n## Forms\n\nA list.\n\n"
            "## Why\n\nNames are read more than written.\n"
        )

        assert outline.format_problems() == (
            "has the heading '## Forms', but holds only a title, the statement and `## Why`",
        )
