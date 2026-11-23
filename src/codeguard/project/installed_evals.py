from importlib.metadata import PackageNotFoundError, requires, version

from packaging.requirements import Requirement

_DISTRIBUTION = "codeguard"
_EVALS = "pydantic-evals"


class IncompatibleEvalsError(Exception):
    pass


def check_installed_evals() -> None:
    requirement = next(
        (
            parsed
            for parsed in map(Requirement, requires(_DISTRIBUTION) or ())
            if parsed.name == _EVALS
        ),
        None,
    )
    if requirement is None:
        raise IncompatibleEvalsError(
            f"codeguard's metadata names no {_EVALS}. Reinstall codeguard."
        )
    try:
        installed = version(_EVALS)
    except PackageNotFoundError:
        raise IncompatibleEvalsError(
            f"{_EVALS} is not installed; codeguard needs {_EVALS}{requirement.specifier}. "
            "Reinstall codeguard."
        ) from None
    if not requirement.specifier.contains(installed, prereleases=True):
        raise IncompatibleEvalsError(
            f"{_EVALS} {installed} is installed; codeguard needs {_EVALS}{requirement.specifier}. "
            "Reinstall codeguard."
        )
