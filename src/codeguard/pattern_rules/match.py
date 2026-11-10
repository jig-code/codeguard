from pydantic import BaseModel, ConfigDict, Field

from codeguard.line_range import LineRange
from codeguard.review import Category, Diagnostic, Severity


class _Position(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    line: int


class _Range(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    start: _Position
    end: _Position


class AstGrepMatch(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    rule_id: str = Field(alias="ruleId")
    file: str
    range: _Range
    message: str
    severity: Severity
    note: str | None

    def diagnostic(self, rule: str) -> Diagnostic:
        return Diagnostic(
            rule=rule,
            file=self.file,
            lines=LineRange(start=self.range.start.line + 1, end=self.range.end.line + 1),
            message=self.message,
            severity=self.severity,
            note=self.note,
            category=Category.PATTERN,
            confidence=1.0,
        )
