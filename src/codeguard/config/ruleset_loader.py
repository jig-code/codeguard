from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path, PurePath
from typing import Self

import yaml
from pydantic import ValidationError

from codeguard.config.bindings_config import BindingsConfig
from codeguard.config.change_kind import ChangeKind
from codeguard.config.config_error import ConfigError
from codeguard.config.config_loader import CONFIG_DIR, CONFIG_FILE
from codeguard.config.gate_rule import GateRule
from codeguard.config.judge_config import JudgeChoice
from codeguard.config.pattern_binding_config import PatternBindingsConfig
from codeguard.config.ruleset import BINDINGS_DIR, Ruleset
from codeguard.config.ruleset_config import RulesetConfig
from codeguard.config.ruleset_structure import RulesetStructure

_PATTERN_BINDING_KEY = "rule"
_BINDING_FILE_SUFFIXES = (".yaml", ".yml")


@dataclass(frozen=True)
class RulesetLoader:
    repo: Path
    root: Path
    name: str | None = None
    selection: RulesetConfig = field(default_factory=RulesetConfig)
    files: frozenset[str] = frozenset()
    package_judge: JudgeChoice = JudgeChoice()

    @classmethod
    def local(cls, working_tree: Path) -> Self:
        return cls(
            repo=working_tree,
            root=working_tree / CONFIG_DIR,
            files=frozenset({PurePath(CONFIG_FILE).name}),
        )

    def check(self) -> None:
        self._raise_problems(RulesetStructure(self.root, self.files).problems())

    def load(self) -> Ruleset:
        self.check()
        bindings_dir = self.root / BINDINGS_DIR
        documents = {
            str(path.relative_to(bindings_dir)): yaml.safe_load(path.read_text())
            for path in sorted(bindings_dir.rglob("*"))
            if path.suffix in _BINDING_FILE_SUFFIXES
        }
        pattern_documents = {
            file: document
            for file, document in documents.items()
            if isinstance(document, dict) and _PATTERN_BINDING_KEY in document
        }
        skill_documents = {
            file: document for file, document in documents.items() if file not in pattern_documents
        }
        try:
            bindings = BindingsConfig.model_validate(
                skill_documents, context={"working_tree": self.repo}
            )
            pattern_bindings = PatternBindingsConfig.model_validate(pattern_documents)
        except ValidationError as error:
            raise ConfigError.invalid(self.root, error, prefix="bindings") from error
        ruleset = Ruleset(
            name=self.name,
            root=self.root,
            bindings=bindings,
            selection=self.selection,
            pattern_bindings=pattern_bindings,
            package_judge=self.package_judge,
        )
        try:
            gates = ruleset.gates()
        except ValidationError as error:
            raise ConfigError.invalid(self.root, error, prefix="gates") from error
        self._raise_problems(
            [
                *self._unbound_pattern_rules(ruleset),
                *self._unknown_triggers(ruleset, gates),
                *self._shared_ids(ruleset, gates),
            ]
        )
        return ruleset

    def _shared_ids(self, ruleset: Ruleset, gates: Mapping[str, GateRule]) -> list[str]:
        if not gates:
            return []
        shared = sorted(ruleset.pattern_rule_ids() & gates.keys())
        return [f"gates.{gate}: a pattern rule has this id" for gate in shared]

    def _unbound_pattern_rules(self, ruleset: Ruleset) -> list[str]:
        if not ruleset.pattern_bindings.root:
            return []
        rules = ruleset.pattern_rule_ids()
        return [
            f"bindings.{file}.rule: no pattern rule {binding.rule}"
            for file, binding in ruleset.pattern_bindings.root.items()
            if binding.rule not in rules
        ]

    def _unknown_triggers(self, ruleset: Ruleset, gates: Mapping[str, GateRule]) -> list[str]:
        if not ruleset.bindings.root:
            return []
        shadowed = [
            f"gates.{gate}: a change kind has this name" for gate in gates if gate in ChangeKind
        ]
        return [
            *shadowed,
            *(
                f"bindings.{file}.triggers: no change kind or gate {trigger}"
                for file, binding in ruleset.bindings.root.items()
                for trigger in sorted(binding.triggers)
                if trigger not in ChangeKind and trigger not in gates
            ),
        ]

    def _raise_problems(self, problems: list[str]) -> None:
        if problems:
            listed = "".join(f"\n  {problem}" for problem in problems)
            raise ConfigError(f"{self.root} is invalid:{listed}")
