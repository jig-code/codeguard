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

_RULE_KEY = "rule"
_SKILL_KEY = "skill"
_BINDING_FILE_SUFFIXES = (".yaml", ".yml")


def _rules_named_alone(documents: Mapping[str, object]) -> dict[str, str]:
    return {
        file: document[_RULE_KEY]
        for file, document in documents.items()
        if isinstance(document, dict)
        and isinstance(document.get(_RULE_KEY), str)
        and _SKILL_KEY not in document
    }


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
        rule_by_file = _rules_named_alone(documents)
        unbound = Ruleset(name=self.name, root=self.root)
        pattern_ids = self._pattern_rule_ids(unbound) if rule_by_file else frozenset()
        self._raise_problems(self._routing_problems(unbound, rule_by_file, pattern_ids))
        pattern_documents = {
            file: documents[file] for file, rule in rule_by_file.items() if rule in pattern_ids
        }
        judge_documents = {
            file: document for file, document in documents.items() if file not in pattern_documents
        }
        try:
            bindings = BindingsConfig.model_validate(
                judge_documents, context={"working_tree": self.repo}
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
                *self._unknown_triggers(ruleset, gates),
                *self._shared_ids(ruleset, gates),
            ]
        )
        return ruleset

    def _routing_problems(
        self, ruleset: Ruleset, rule_by_file: Mapping[str, str], pattern_ids: frozenset[str]
    ) -> list[str]:
        return [
            problem
            for file, rule in rule_by_file.items()
            if (problem := self._route_problem(ruleset, file, rule, rule in pattern_ids))
        ]

    def _pattern_rule_ids(self, ruleset: Ruleset) -> frozenset[str]:
        try:
            return ruleset.pattern_rule_ids()
        except ValidationError as error:
            raise ConfigError.invalid(self.root, error, prefix="rules") from error

    def _route_problem(
        self, ruleset: Ruleset, file: str, rule: str, is_pattern_rule: bool
    ) -> str | None:
        if "/" in rule or "\\" in rule:
            return f"bindings.{file}.rule: {rule!r} is not a rule id"
        path = ruleset.judge_rule_path(rule)
        expected = path.relative_to(self.root)
        if path.is_file() and is_pattern_rule:
            return f"bindings.{file}.rule: both {expected} and pattern rule {rule} have this id"
        if not path.is_file() and not is_pattern_rule:
            return f"bindings.{file}.rule: no judge rule {expected} or pattern rule {rule}"
        return None

    def _shared_ids(self, ruleset: Ruleset, gates: Mapping[str, GateRule]) -> list[str]:
        if not gates:
            return []
        shared = sorted(ruleset.pattern_rule_ids() & gates.keys())
        return [f"gates.{gate}: a pattern rule has this id" for gate in shared]

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
