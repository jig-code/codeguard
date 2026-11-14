import factory

from codeguard.repository import AddedRow, ChangedLines, FileDiff, RowText


class MakeChangedLinesBase(factory.Factory):
    class Meta:
        model = ChangedLines
        abstract = True

    file = "a.py"


class MakeChangedLines(MakeChangedLinesBase):
    rows = (AddedRow(1, RowText(b"print(1)")),)

    @classmethod
    def _create(cls, model_class, **kwargs):
        file = kwargs["file"]
        return model_class({file: FileDiff.from_whole_file_rows(file, kwargs["rows"])})


class MakeNewFileChangedLines(MakeChangedLinesBase):
    content = b"print(1)\n"

    @classmethod
    def _create(cls, model_class, **kwargs):
        return model_class({kwargs["file"]: FileDiff.from_new_file(kwargs["content"])})
