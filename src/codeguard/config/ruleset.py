import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import ValidationError

from codeguard.config.binding_config import LEGACY_SKILL_FILE, BindingConfig
from codeguard.config.bindings_config import BindingsConfig
from codeguard.config.change_kind import ChangeKind
from codeguard.config.config_error import ConfigError
from codeguard.config.gate_rule import GateRule
from codeguard.config.judge_config import JudgeChoice
from codeguard.config.path_scope import PathScope
from codeguard.config.pattern_binding_config import PatternBindingsConfig
from codeguard.config.pattern_rule import PatternRule
from codeguard.config.ruleset_config import RulesetConfig

PATTERN_RULE_DIR = "rules/pattern"
GATE_DIR = "gates"
RULE_TEST_DIR = "rule-tests"
SNAPSHOT_DIR = f"{RULE_TEST_DIR}/__snapshots__"
LEGACY_PATTERN_TEST_DIR = f"{RULE_TEST_DIR}/pattern"
JUDGE_EVAL_DIR = "rule-evals"
BINDINGS_DIR = "bindings"
JUDGE_RULE_DIR = "rules/judge"
SKILLS_DIR = "skills"
_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


@dataclass(frozen=True)
class Ruleset:
    name: str | None
    root: Path
    bindings: BindingsConfig = BindingsConfig({})
    selection: RulesetConfig = field(default_factory=RulesetConfig)
    pattern_bindings: PatternBindingsConfig = PatternBindingsConfig({})
    # Outside CI, as in the agent's Stop hook, the rules the selection marks `ci_only` are off.
    skip_ci_only: bool = False
    package_judge: JudgeChoice = JudgeChoice()

    def excludes(self, rule: str) -> bool:
        return self.selection.excludes(rule) or (
            self.skip_ci_only and self.selection.is_ci_only(rule)
        )

    def qualified_rule_id(self, rule_id: str) -> str:
        return rule_id if self.name is None else f"{self.name}/{rule_id}"

    def judged_rule_ids(self) -> frozenset[str]:
        return frozenset(binding.rule_id for binding in self.bindings.root.values())

    def judge_rule_path(self, rule: str) -> Path:
        return self.root / JUDGE_RULE_DIR / f"{rule}.md"

    def _judge_rule_file(self, binding: BindingConfig) -> Path:
        if binding.skill is not None:
            return binding.skill / LEGACY_SKILL_FILE
        return self.judge_rule_path(binding.rule_id)

    def judge_rule_text(self, binding: BindingConfig) -> str:
        text = self._judge_rule_file(binding).read_text()
        if binding.skill is not None:
            return _FRONTMATTER.sub("", text, count=1)
        return text

    def pattern_rule_ids(self) -> frozenset[str]:
        return frozenset(rule.id for rule in self.pattern_rules())

    def pattern_rules(self) -> list[PatternRule]:
        rule_dir = self.root / PATTERN_RULE_DIR
        try:
            return [
                PatternRule.model_validate(document)
                for path in sorted(rule_dir.rglob("*.y*ml"))
                for document in yaml.safe_load_all(path.read_text())
                if document
            ]
        except ValidationError as error:
            raise ConfigError.invalid(self.root, error, prefix="rules") from error

    def gates(self) -> dict[str, GateRule]:
        gate_dir = self.root / GATE_DIR
        gates = (
            GateRule.model_validate(document)
            for path in sorted(gate_dir.rglob("*.y*ml"))
            for document in yaml.safe_load_all(path.read_text())
            if document
        )
        return {gate.id: gate for gate in gates}

    def qualified_gates(self) -> dict[str, GateRule]:
        return {self.qualified_trigger(gate): rule for gate, rule in self.gates().items()}

    def qualified_trigger(self, trigger: str) -> str:
        return trigger if trigger in ChangeKind else f"gate:{self.qualified_rule_id(trigger)}"

    def selected_bindings(self) -> dict[str, BindingConfig]:
        return {
            self.qualified_rule_id(binding.rule_id): self._qualified(
                self.selection.apply(binding.rule_id, binding)
            )
            for binding in self.bindings.root.values()
            if not self.excludes(binding.rule_id)
        }

    def judge_choice(
        self, binding: BindingConfig, project_judge: JudgeChoice, judge_override: JudgeChoice
    ) -> JudgeChoice:
        if judge_override.provider:
            return judge_override
        return binding.judge.over(project_judge).over(self.package_judge)

    def _qualified(self, binding: BindingConfig) -> BindingConfig:
        triggers = frozenset(self.qualified_trigger(trigger) for trigger in binding.triggers)
        return binding.model_copy(update={"triggers": triggers})

    def pattern_scope(self, rule: str) -> PathScope:
        return self.selection.apply_scope(rule, self.pattern_bindings.scope(rule))
