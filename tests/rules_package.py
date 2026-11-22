import shutil
from pathlib import Path

from git_repo import GitRepo

EXAMPLE_PACKAGE = Path(__file__).parent / "data/example-package"
NO_PRINT_RULE_FILE = EXAMPLE_PACKAGE / "python/rules/pattern/no-print.yml"
PLACEMENT_RULE = (EXAMPLE_PACKAGE / "python/rules/judge/responsibility-placement.md").read_text()


def write_package(repo: GitRepo, prefix: str = "") -> None:
    shutil.copytree(EXAMPLE_PACKAGE, repo.root / prefix, dirs_exist_ok=True)
