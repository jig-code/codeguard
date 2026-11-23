from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, requires, version
from typing import Self

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet

_DISTRIBUTION = "codeguard"
_EVALS = "pydantic-evals"


class IncompatibleEvalsError(Exception):
    pass


@dataclass(frozen=True)
class InstalledEvals:
    required: SpecifierSet | None
    version: str | None

    @classmethod
    def load(cls) -> Self:
        required = next(
            (
                requirement.specifier
                for requirement in map(Requirement, requires(_DISTRIBUTION) or ())
                if requirement.name == _EVALS
            ),
            None,
        )
        try:
            installed = version(_EVALS)
        except PackageNotFoundError:
            installed = None
        return cls(required, installed)

    def check(self) -> None:
        if self.required is None:
            raise IncompatibleEvalsError(
                f"codeguard's metadata names no {_EVALS}. Reinstall codeguard."
            )
        if self.version is None:
            raise IncompatibleEvalsError(
                f"{_EVALS} is not installed; codeguard needs {_EVALS}{self.required}. "
                "Reinstall codeguard."
            )
        if not self.required.contains(self.version, prereleases=True):
            raise IncompatibleEvalsError(
                f"{_EVALS} {self.version} is installed; codeguard needs "
                f"{_EVALS}{self.required}. Reinstall codeguard."
            )
