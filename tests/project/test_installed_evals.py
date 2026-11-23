from importlib.metadata import PackageNotFoundError

import pytest

from codeguard.project import IncompatibleEvalsError, check_installed_evals, installed_evals


class TestCheckInstalledEvals:
    def test_installed_version_in_the_required_range_passes(self):
        check_installed_evals()

    def test_installed_version_outside_the_required_range_is_an_error(self, monkeypatch):
        monkeypatch.setattr(installed_evals, "version", lambda _: "3.0.0")

        with pytest.raises(IncompatibleEvalsError) as error:
            check_installed_evals()

        assert str(error.value).startswith(
            "pydantic-evals 3.0.0 is installed; codeguard needs pydantic-evals~="
        )

    def test_missing_install_is_an_error(self, monkeypatch):
        def not_installed(name):
            raise PackageNotFoundError(name)

        monkeypatch.setattr(installed_evals, "version", not_installed)

        with pytest.raises(IncompatibleEvalsError) as error:
            check_installed_evals()

        assert str(error.value).startswith(
            "pydantic-evals is not installed; codeguard needs pydantic-evals~="
        )

    def test_metadata_without_the_requirement_is_an_error(self, monkeypatch):
        monkeypatch.setattr(installed_evals, "requires", lambda _: ["pyyaml>=6"])

        with pytest.raises(IncompatibleEvalsError) as error:
            check_installed_evals()

        assert str(error.value) == (
            "codeguard's metadata names no pydantic-evals. Reinstall codeguard."
        )
