import factory

from codeguard.config import ChangeKind
from codeguard.syntax import FileClassification


class MakeFileClassification(factory.Factory):
    class Meta:
        model = FileClassification

    touched_kinds = frozenset({ChangeKind.ANY})
    context_lines = frozenset({1})
