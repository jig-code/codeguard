from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

from codeguard.config import JudgeModel
from codeguard.review.deadline import Deadline
from codeguard.review.judge import Judge


class JudgeFactory(Protocol):
    def __call__(
        self, root: Path, model: JudgeModel, deadline: Deadline | None = None
    ) -> Judge: ...

    def require_sign_in_for(self, models: Iterable[JudgeModel]) -> None: ...
