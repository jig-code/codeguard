import pytest

from codeguard.cli.installed_evals import IncompatibleEvalsError, InstalledEvals


class TestInstalledEvals:
    def test_codeguard_s_own_install_passes(self):
        InstalledEvals.load().check()

    def test_installed_version_outside_the_required_range_is_an_error(self):
        installed = InstalledEvals(("pydantic-evals~=1.2",), "3.0.0")

        with pytest.raises(IncompatibleEvalsError) as error:
            installed.check()

        assert str(error.value) == (
            "pydantic-evals 3.0.0 is installed; codeguard needs pydantic-evals~=1.2. "
            "Reinstall codeguard."
        )

    def test_missing_install_is_an_error(self):
        installed = InstalledEvals(("pydantic-evals~=1.2",), None)

        with pytest.raises(IncompatibleEvalsError) as error:
            installed.check()

        assert str(error.value) == (
            "pydantic-evals is not installed; codeguard needs pydantic-evals~=1.2. "
            "Reinstall codeguard."
        )

    def test_metadata_without_the_requirement_is_an_error(self):
        installed = InstalledEvals(("pyyaml>=6",), "1.4.0")

        with pytest.raises(IncompatibleEvalsError) as error:
            installed.check()

        assert str(error.value) == (
            "codeguard's metadata names no pydantic-evals. Reinstall codeguard."
        )
