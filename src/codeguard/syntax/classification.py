from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class FileClassification:
    """What the change classifier found in a changed file: the change kinds the change
    touches, None in a language without change kinds, the lines the judge is shown, and the
    lines of each kind's nodes around the change. A file a classification holds nothing for
    fires every trigger and is judged whole."""

    kinds: frozenset[str] | None
    judged: frozenset[int]
    kind_lines: Mapping[str, frozenset[int]] = field(default_factory=dict)

    def judged_lines(self, triggers: frozenset[str]) -> frozenset[int]:
        return self.judged.union(*(self.kind_lines.get(kind, frozenset()) for kind in triggers))


type Classification = Mapping[str, FileClassification]
