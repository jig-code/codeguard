from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LineRange(BaseModel):
    """Lines `start` to `end` of a file, both included."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    start: int = Field(description="The first line.")
    end: int = Field(description="The last line: the same as `start` for one line.")

    @model_validator(mode="after")
    def validate_end_is_not_before_start(self) -> Self:
        if self.end < self.start:
            raise ValueError(f"end {self.end} is before start {self.start}")
        return self

    @property
    def numbers(self) -> range:
        return range(self.start, self.end + 1)

    @property
    def described(self) -> str:
        return f"line {self}" if self.start == self.end else f"lines {self}"

    def __contains__(self, line: int) -> bool:
        return self.start <= line <= self.end

    def __str__(self) -> str:
        return str(self.start) if self.start == self.end else f"{self.start}-{self.end}"
