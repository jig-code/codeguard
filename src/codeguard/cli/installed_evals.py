from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, requires, version
from typing import Self

from packaging.requirements import Requirement

_DISTRIBUTION = "codeguard"
_EVALS = "pydantic-evals"


class IncompatibleEvalsError(Exception):
    pass


@dataclass(frozen=True)
class InstalledEvals:
    codeguard_requires: tuple[str, ...]
    version: str | None

    @classmethod
    def load(cls) -> Self:
        try:
            installed = version(_EVALS)
        except PackageNotFoundError:
            installed = None
        return cls(tuple(requires(_DISTRIBUTION) or ()), installed)

    def check(self) -> None:
        requirement = next(
            (
                parsed
                for parsed in map(Requirement, self.codeguard_requires)
                if parsed.name == _EVALS
            ),
            None,
        )
        if requirement is None:
            raise IncompatibleEvalsError(
                f"codeguard's metadata names no {_EVALS}. Reinstall codeguard."
            )
        if self.version is None:
            raise IncompatibleEvalsError(
                f"{_EVALS} is not installed; codeguard needs {_EVALS}{requirement.specifier}. "
                "Reinstall codeguard."
            )
        if not requirement.specifier.contains(self.version, prereleases=True):
            raise IncompatibleEvalsError(
                f"{_EVALS} {self.version} is installed; codeguard needs "
                f"{_EVALS}{requirement.specifier}. Reinstall codeguard."
            )
