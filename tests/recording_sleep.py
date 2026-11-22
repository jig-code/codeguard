from dataclasses import dataclass, field


@dataclass
class RecordingSleep:
    waited: list[float] = field(default_factory=list)

    async def __call__(self, seconds: float) -> None:
        self.waited.append(seconds)
