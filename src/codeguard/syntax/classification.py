from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Classification:
    """What the change classifier found in each changed file: the change kinds the change
    touches, the lines the judge is shown, and the lines of each kind's nodes around the
    change. A file it holds nothing for fires every trigger and is judged whole."""

    kinds: Mapping[str, frozenset[str]] = field(default_factory=dict)
    judged: Mapping[str, frozenset[int]] = field(default_factory=dict)
    kind_lines: Mapping[str, Mapping[str, frozenset[int]]] = field(default_factory=dict)

    def kinds_of(self, file: str) -> frozenset[str] | None:
        return self.kinds.get(file)

    def judged_lines(
        self, file: str, triggers: frozenset[str] = frozenset()
    ) -> frozenset[int] | None:
        judged = self.judged.get(file)
        if judged is None:
            return None
        spans = self.kind_lines.get(file, {})
        return judged.union(*(spans.get(kind, frozenset()) for kind in triggers))
