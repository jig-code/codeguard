import pytest
from packaging.specifiers import SpecifierSet

from codeguard.cli.installed_evals import IncompatibleEvalsError, InstalledEvals


class TestInstalledEvals:
    def test_loaded_install_passes_the_check(self):
        InstalledEvals.load().check()

    def test_installed_version_outside_the_required_range_is_an_error(self):
        installed = InstalledEvals(SpecifierSet("~=1.2"), "3.0.0")

        with pytest.raises(IncompatibleEvalsError) as error:
            installed.check()

        assert str(error.value) == (
            "pydantic-evals 3.0.0 is installed; codeguard needs pydantic-evals~=1.2. "
            "Reinstall codeguard."
        )

    def test_missing_install_is_an_error(self):
        installed = InstalledEvals(SpecifierSet("~=1.2"), None)

        with pytest.raises(IncompatibleEvalsError) as error:
            installed.check()

        assert str(error.value) == (
            "pydantic-evals is not installed; codeguard needs pydantic-evals~=1.2. "
            "Reinstall codeguard."
        )

    def test_metadata_without_the_requirement_is_an_error(self):
        installed = InstalledEvals(None, "1.4.0")

        with pytest.raises(IncompatibleEvalsError) as error:
            installed.check()

        assert str(error.value) == (
            "codeguard's metadata names no pydantic-evals. Reinstall codeguard."
        )
