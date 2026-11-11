import factory

from codeguard.config import ChangeKind
from codeguard.syntax import FileClassification


class MakeFileClassification(factory.Factory):
    class Meta:
        model = FileClassification

    kinds = frozenset({ChangeKind.ANY})
    judged = frozenset({1})
    kind_lines = factory.LazyFunction(dict)
