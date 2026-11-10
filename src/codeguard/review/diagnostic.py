import hashlib
import textwrap
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from codeguard.config import Severity
from codeguard.line_range import LineRange


class Category(StrEnum):
    PATTERN = "pattern"
    JUDGED = "judged"
    JUDGE_ERROR = "judge_error"


class ErrorType(StrEnum):
    TIMEOUT = "timeout"
    PROCESS = "process"
    NO_VERDICT = "no_verdict"


class Diagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rule: str
    file: str
    lines: LineRange | None
    message: str
    severity: Severity
    note: str | None
    category: Category
    confidence: float = Field(ge=0, le=1)
    error_type: ErrorType | None = None

    @model_validator(mode="after")
    def _error_type_only_on_judge_errors(self) -> Self:
        if (self.category is Category.JUDGE_ERROR) != (self.error_type is not None):
            raise ValueError("a judge_error diagnostic, and only one, has an error_type")
        return self

    @property
    def id(self) -> str:
        key = f"{self.rule}:{self.file}:{self.lines}"
        return hashlib.sha256(key.encode()).hexdigest()[:12]

    @property
    def blocks(self) -> bool:
        return self.severity is Severity.ERROR

    def as_warning(self) -> Self:
        return self.model_copy(update={"severity": Severity.WARNING})

    def as_json(self) -> dict[str, object]:
        return {
            "id": self.id,
            "rule": self.rule,
            "file": self.file,
            "lines": None if self.lines is None else self.lines.model_dump(),
            "message": self.message,
            "severity": self.severity,
            "category": self.category,
            "confidence": self.confidence,
            "error_type": self.error_type,
            "note": None if self.category is Category.JUDGED else self.note,
            "blocks": self.blocks,
        }

    def __str__(self) -> str:
        location = self.file if self.lines is None else f"{self.file}:{self.lines}"
        confidence = (
            f" (confidence {self.confidence:.2f})" if self.category is Category.JUDGED else ""
        )
        summary = f"{location}: {self.severity} {self.rule}: {self.message}{confidence} [{self.id}]"
        if self.note is None:
            return summary
        return f"{summary}\n{textwrap.indent(self.note.rstrip(), '  ')}"
