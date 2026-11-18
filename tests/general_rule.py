RULE = "knowledge-stated-once"
RULE_FILE = f".codeguard/rules/judge/{RULE}.md"
BINDING = f".codeguard/bindings/{RULE}.yaml"
EVAL = f".codeguard/rule-evals/{RULE}.yaml"
GENERAL_RULE = (
    "# Knowledge stated once\n\nEach piece of knowledge has one home in the code.\n\n"
    "## Why\n\nTwo copies of one fact drift apart when only one is changed.\n"
)
BOTH_LANGUAGES = 'paths: ["**/*.py", "**/*.ts"]\ntriggers: [string-literal]\n'


def case(name: str, file: str, after: str, outcome: str = "invalid") -> str:
    return (
        f"  - name: {name}\n    inputs:\n      file: {file}\n      after: |\n        {after}\n"
        f"    expected_output:\n      outcome: {outcome}\n"
    )


PYTHON_CASE = case("a repeated status literal", "orders.py", 'STATUS = "shipped"')
TYPESCRIPT_CASE = case("a repeated status literal in a script", "orders.ts", "const s = 'shipped';")
