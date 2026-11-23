import os
from pathlib import Path
from unittest import mock

from codeguard.rules.cache_directory import cache_directory


class TestCacheDirectory:
    @mock.patch.dict(os.environ, {"XDG_CACHE_HOME": "/var/cache/someone"})
    def test_is_under_the_xdg_cache_home(self):
        assert cache_directory("judgements") == Path("/var/cache/someone/codeguard/judgements")

    def test_is_under_the_home_cache_without_an_xdg_cache_home(self, tmp_path, monkeypatch):
        monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))

        assert cache_directory("packages") == tmp_path / ".cache/codeguard/packages"

    def test_empty_xdg_cache_home_counts_as_unset(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CACHE_HOME", "")
        monkeypatch.setenv("HOME", str(tmp_path))

        assert cache_directory("packages") == tmp_path / ".cache/codeguard/packages"
