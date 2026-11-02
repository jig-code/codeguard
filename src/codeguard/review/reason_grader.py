from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

INSTRUCTIONS = (Path(__file__).parent / "reason_grader.md").read_text()


@dataclass(frozen=True)
class GradeRequest:
    """Two reasons for one verdict: the one a rule eval case expects and the one the judge gave."""

    expected: str
    given: str

    @property
    def instructions(self) -> str:
        return INSTRUCTIONS

    @property
    def prompt(self) -> str:
        return f"<expected>\n{self.expected}\n</expected>\n\n<given>\n{self.given}\n</given>\n"


class Agreement(BaseModel):
    """Whether the given reason gives the same ground as the expected one."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    agrees: bool = Field(
        description="Whether the given reason rests the verdict on the same ground as the expected."
    )
    why: str = Field(
        description="What the two reasons share, or where they part, in one plain sentence."
    )


class Grader(Protocol):
    def grade(self, request: GradeRequest) -> Agreement: ...
