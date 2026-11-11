import factory

from codeguard.repository import AddedRow, ChangedLines, FileDiff, KeptRow, RowText


class MakeAnyChangedLines(factory.Factory):
    class Meta:
        model = ChangedLines
        abstract = True

    file = "a.py"


class MakeChangedLines(MakeAnyChangedLines):
    class Params:
        return_line_added = factory.Trait(
            file="pricing.py",
            rows=(
                KeptRow(1, 1),
                KeptRow(2, 2),
                KeptRow(3, 3),
                KeptRow(4, 4),
                AddedRow(5, RowText(b"    return total - DISCOUNT")),
            ),
        )

    rows = (AddedRow(1, RowText(b"print(1)")),)

    @classmethod
    def _create(cls, model_class, **kwargs):
        file = kwargs["file"]
        return model_class({file: FileDiff.from_whole_file_rows(file, kwargs["rows"])})


class MakeNewFileChangedLines(MakeAnyChangedLines):
    content = b"print(1)\n"

    @classmethod
    def _create(cls, model_class, **kwargs):
        return model_class({kwargs["file"]: FileDiff.of_new_file(kwargs["content"])})
