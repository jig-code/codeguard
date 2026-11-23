from importlib import metadata

import yaml
from packaging.version import Version

from codeguard.ast_grep import AstGrep
from codeguard.project import Project
from codeguard.repository import WorkingTree


class TestProject:
    def test_ast_grep_is_the_version_the_config_pins(self, directory):
        bundled = metadata.version("ast-grep-cli")
        directory.write(".codeguard/config.yaml", yaml.safe_dump({"ast-grep": bundled}))

        project = Project.load(WorkingTree.at(directory.root))

        assert project.ast_grep == AstGrep(Version(bundled))
