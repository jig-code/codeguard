from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import TextIO


class CallStatus(StrEnum):
    NEW = "new"
    CACHED = "cached"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class PlannedCall:
    rule: str
    file: str
    cached: bool
    triggered: bool

    @property
    def status(self) -> CallStatus:
        if not self.triggered:
            return CallStatus.SKIPPED
        return CallStatus.CACHED if self.cached else CallStatus.NEW


@dataclass(frozen=True)
class JudgePlan:
    calls: tuple[PlannedCall, ...]

    def write(self, out: TextIO) -> None:
        made = [call for call in self.calls if call.triggered]
        cached = [call for call in made if call.cached]
        out.write(
            f"Judge calls: {len(made)} ({len(cached)} cached, {len(made) - len(cached)} new), "
            f"{len(self.calls) - len(made)} skipped by triggers\n"
        )
        self._write_totals(out, "rule", lambda call: call.rule)
        self._write_totals(out, "file", lambda call: call.file)
        self._write_calls_by_file(out)

    def _write_totals(self, out: TextIO, heading: str, key: Callable[[PlannedCall], str]) -> None:
        if not self.calls:
            return
        totals: dict[str, dict[CallStatus, int]] = {}
        for call in self.calls:
            counts = totals.setdefault(key(call), dict.fromkeys(CallStatus, 0))
            counts[call.status] += 1
        out.write(f"\nBy {heading}:\n     new  cached  skipped  {heading}\n")
        for name, counts in sorted(
            totals.items(),
            key=lambda item: (-item[1][CallStatus.NEW] - item[1][CallStatus.CACHED], item[0]),
        ):
            out.write(
                f"  {counts[CallStatus.NEW]:>6}  {counts[CallStatus.CACHED]:>6}  "
                f"{counts[CallStatus.SKIPPED]:>7}  {name}\n"
            )

    def _write_calls_by_file(self, out: TextIO) -> None:
        if not self.calls:
            return
        out.write("\nCalls by file:\n")
        for file in sorted({call.file for call in self.calls}):
            out.write(f"{file}\n")
            for call in sorted(
                (call for call in self.calls if call.file == file),
                key=lambda call: (call.status is CallStatus.SKIPPED, call.rule),
            ):
                out.write(f"  {call.status:<8} {call.rule}\n")
