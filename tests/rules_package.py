from git_repo import GitRepo

NO_PRINT_RULE = (
    "id: no-print\n"
    "language: python\n"
    "severity: error\n"
    "message: Use logging, not print.\n"
    "metadata:\n"
    "  why: Print output skips the log levels and handlers production reads.\n"
    "rule:\n"
    "  pattern: print($$$ARGS)\n"
)
PLACEMENT_RULE = (
    "# Responsibility placement\n\nA method lives on the type whose data it reads.\n\n"
    "## Why\n\nLogic away from its data is missed when the data changes.\n"
)


def write_package(repo: GitRepo, prefix: str = "") -> None:
    repo.write(f"{prefix}codeguard-package.yaml", "name: example\nrulesets: [python]\n")
    repo.write(f"{prefix}python/rules/pattern/no-print.yml", NO_PRINT_RULE)
    repo.write(f"{prefix}python/rules/judge/responsibility-placement.md", PLACEMENT_RULE)
    repo.write(
        f"{prefix}python/bindings/responsibility-placement.yaml",
        'rule: responsibility-placement\npaths: ["**/*.py"]\ntriggers: [any]\n',
    )
