import factory

from codeguard.repository import AddedRow, ChangedLines, FileDiff, RowText


class MakeChangedLines(factory.Factory):
    class Meta:
        model = ChangedLines

    file = "a.py"
    rows = (AddedRow(1, RowText(b"print(1)")),)

    @classmethod
    def _create(cls, model_class, **kwargs):
        file = kwargs["file"]
        return model_class({file: FileDiff.from_whole_file_rows(file, kwargs["rows"])})


class MakeNewFileChangedLines(factory.Factory):
    class Meta:
        model = ChangedLines

    file = "a.py"
    content = b"print(1)\n"

    @classmethod
    def _create(cls, model_class, **kwargs):
        return model_class({kwargs["file"]: FileDiff.of_new_file(kwargs["content"])})
