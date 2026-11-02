from pathlib import Path
from typing import Protocol

from codeguard.config import JudgeModel
from codeguard.review import Grader


class GraderFactory(Protocol):
    def __call__(self, root: Path, model: JudgeModel) -> Grader: ...
