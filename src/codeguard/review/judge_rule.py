from dataclasses import dataclass


@dataclass(frozen=True)
class JudgeRule:
    name: str
    text: str
