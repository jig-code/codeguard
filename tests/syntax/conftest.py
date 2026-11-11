import pytest

from codeguard.repository import LineScopes, WorkingTree


@pytest.fixture
def working_tree(git_repo) -> WorkingTree:
    return WorkingTree.at(git_repo.root)


@pytest.fixture
def line_scopes(working_tree) -> LineScopes:
    return LineScopes(working_tree)
