import subprocess

import pytest
import yaml
from git_repo import GitRepo

from codeguard.packages import GitFetch

MANIFEST = yaml.safe_dump({"name": "example", "rulesets": ["python"]})


@pytest.fixture
def remote(tmp_path_factory: pytest.TempPathFactory) -> GitRepo:
    repo = GitRepo.init(tmp_path_factory.mktemp("remote").resolve())
    repo.write("codeguard-package.yaml", MANIFEST)
    repo.commit("Add manifest")
    repo.git("tag", "v1.0.0")
    return repo


class TestGitFetch:
    def test_fetches_a_tag(self, remote, tmp_path):
        checkout = GitFetch(tmp_path).fetch(remote.file_url, "v1.0.0")

        assert (checkout / "codeguard-package.yaml").read_text() == MANIFEST

    def test_fetches_a_commit(self, remote, tmp_path):
        checkout = GitFetch(tmp_path).fetch(remote.file_url, remote.head())

        assert (checkout / "codeguard-package.yaml").read_text() == MANIFEST

    def test_fetched_ref_is_reused_without_the_remote(self, remote, tmp_path):
        fetch = GitFetch(tmp_path)
        first = fetch.fetch(remote.file_url, "v1.0.0")
        remote.write(
            "codeguard-package.yaml", yaml.safe_dump({"name": "changed", "rulesets": ["python"]})
        )
        remote.commit("Change manifest")
        remote.git("tag", "--force", "v1.0.0")

        second = fetch.fetch(remote.file_url, "v1.0.0")

        assert second == first
        assert (second / "codeguard-package.yaml").read_text() == MANIFEST

    def test_unknown_ref_is_an_error_and_caches_nothing(self, remote, tmp_path):
        with pytest.raises(subprocess.CalledProcessError):
            GitFetch(tmp_path).fetch(remote.file_url, "v9.9.9")

        assert list(tmp_path.iterdir()) == []
