from dataclasses import dataclass
from pathlib import Path
from typing import Self

from codeguard.ast_grep import AstGrep
from codeguard.config import Config, ConfigLoader
from codeguard.repository import WorkingTree


@dataclass(frozen=True)
class Project:
    working_tree: WorkingTree
    config: Config
    ast_grep: AstGrep

    @classmethod
    def load(cls, working_tree: WorkingTree) -> Self:
        config = ConfigLoader(working_tree.root).load()
        ast_grep = AstGrep(config.ast_grep)
        ast_grep.check_supported()
        return cls(working_tree, config, ast_grep)

    @property
    def root(self) -> Path:
        return self.working_tree.root
