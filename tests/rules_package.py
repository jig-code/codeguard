import yaml
from git_repo import GitRepo

NO_PRINT_RULE = {
    "id": "no-print",
    "language": "python",
    "severity": "error",
    "message": "Use logging, not print.",
    "metadata": {"why": "Print output skips the log levels and handlers production reads."},
    "rule": {"pattern": "print($$$ARGS)"},
}
PLACEMENT_RULE = (
    "# Responsibility placement\n\nA method lives on the type whose data it reads.\n\n"
    "## Why\n\nLogic away from its data is missed when the data changes.\n"
)


def write_package(repo: GitRepo, prefix: str = "") -> None:
    repo.write(
        f"{prefix}codeguard-package.yaml",
        yaml.safe_dump({"name": "example", "rulesets": ["python"]}),
    )
    repo.write(f"{prefix}python/rules/pattern/no-print.yml", yaml.safe_dump(NO_PRINT_RULE))
    repo.write(f"{prefix}python/rules/judge/responsibility-placement.md", PLACEMENT_RULE)
    repo.write(
        f"{prefix}python/bindings/responsibility-placement.yaml",
        yaml.safe_dump(
            {"rule": "responsibility-placement", "paths": ["**/*.py"], "triggers": ["any"]}
        ),
    )
