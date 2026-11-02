from git_repo import GitRepo

RULE = "knowledge-stated-once"
SKILL_DIR = f".codeguard/skills/{RULE}"
BINDING = f".codeguard/bindings/{RULE}.yaml"
EVAL = f".codeguard/rule-evals/{RULE}.yaml"
GENERAL_SKILL = (
    "# Knowledge stated once\n\nEach piece of knowledge has one home in the code.\n\n"
    "## Why\n\nTwo copies of one fact drift apart when only one is changed.\n"
)
PYTHON_SUPPLEMENT = "## In Python\n\nA module-level constant is the home of a value.\n"
BOTH_LANGUAGES = 'paths: ["**/*.py", "**/*.ts"]\ntriggers: [string-literal]\n'


def case(name: str, file: str, after: str, outcome: str = "invalid") -> str:
    return (
        f"  - name: {name}\n    inputs:\n      file: {file}\n      after: |\n        {after}\n"
        f"    expected_output:\n      outcome: {outcome}\n"
    )


PYTHON_CASE = case("repeats a status literal", "orders.py", 'STATUS = "shipped"')
TYPESCRIPT_CASE = case("repeats a status literal in a script", "orders.ts", "const s = 'shipped';")


def write_general_rule(repo: GitRepo, binding: str = BOTH_LANGUAGES) -> None:
    """A rule for Python and TypeScript files, with a Python supplement."""
    repo.write(f"{SKILL_DIR}/SKILL.md", GENERAL_SKILL)
    repo.write(f"{SKILL_DIR}/python.md", PYTHON_SUPPLEMENT)
    repo.write(BINDING, f"skill: {SKILL_DIR}\n{binding}")
