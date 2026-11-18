import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from codeguard.config import ConfigError, RulesetLoader
from codeguard.rule_tests.rule_test_result import RuleTestResult

# A `## Why` heading followed by text before the next heading of its level or above.
_WHY_SECTION = re.compile(r"^##[ \t]+Why[ \t]*\n(?P<body>(?:(?!#{1,2}[ \t]).*\n?)*)", re.MULTILINE)


class MissingWhyMode(StrEnum):
    WARN = "warn"
    FAIL = "fail"
    OFF = "off"

    def result(self, missing: tuple[str, ...]) -> RuleTestResult:
        if self is MissingWhyMode.FAIL:
            return RuleTestResult(problems=missing)
        if self is MissingWhyMode.WARN:
            return RuleTestResult(warnings=missing)
        return RuleTestResult()


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
        judge_rules = {
            binding.rule_id: ruleset.judge_rule_text(binding)
            for binding in ruleset.bindings.root.values()
        }
        return self.mode.result(rules_without_why(judge_rules, ruleset.pattern_rules_without_why()))


def rules_without_why(
    judge_rules: Mapping[str, str], pattern_rules_without_why: Iterable[str]
) -> tuple[str, ...]:
    return (
        *(
            f"{rule}: no ## Why section in its rule file"
            for rule, text in sorted(judge_rules.items())
            if not has_why_section(text)
        ),
        *(f"{rule}: no metadata.why" for rule in pattern_rules_without_why),
    )


def has_why_section(rule: str) -> bool:
    match = _WHY_SECTION.search(rule)
    return match is not None and bool(match.group("body").strip())
