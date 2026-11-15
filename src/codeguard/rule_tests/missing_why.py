import re
from dataclasses import dataclass
from enum import StrEnum

from codeguard.config import JUDGE_RULE_DIR, ConfigError, RulesetLoader
from codeguard.rule_tests.rule_test_result import RuleTestResult

# A `## Why` heading followed by text before the next heading of its level or above.
_WHY_SECTION = re.compile(r"^##[ \t]+Why[ \t]*\n(?P<body>(?:(?!#{1,2}[ \t]).*\n?)*)", re.MULTILINE)


class MissingWhyMode(StrEnum):
    WARN = "warn"
    FAIL = "fail"
    OFF = "off"


@dataclass(frozen=True)
class MissingWhy:
    """Report each rule that doesn't say why it exists: a judge rule's `## Why` section,
    a pattern rule's `metadata.why`. A rule nobody can trace to a reason can't be
    reviewed when the code or the design around it changes."""

    ruleset: RulesetLoader
    mode: MissingWhyMode = MissingWhyMode.WARN

    def run(self) -> RuleTestResult:
        if self.mode is MissingWhyMode.OFF:
            return RuleTestResult()
        try:
            ruleset = self.ruleset.load()
        except ConfigError:
            # BroadTriggers already reports an invalid ruleset.
            return RuleTestResult()
        judged = sorted(
            binding.rule
            for binding in ruleset.bindings.root.values()
            if not has_why_section(ruleset.judge_rule_file(binding.rule).read_text())
        )
        missing = (
            *(f"{rule}: no ## Why section in {JUDGE_RULE_DIR}/{rule}.md" for rule in judged),
            *(f"{rule}: no metadata.why" for rule in ruleset.pattern_rules_without_why()),
        )
        if self.mode is MissingWhyMode.FAIL:
            return RuleTestResult(problems=missing)
        return RuleTestResult(warnings=missing)


def has_why_section(rule: str) -> bool:
    match = _WHY_SECTION.search(rule)
    return match is not None and bool(match.group("body").strip())
