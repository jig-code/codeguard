RULE = "knowledge-stated-once"
RULE_FILE = f".codeguard/rules/judge/{RULE}.md"
BINDING = f".codeguard/bindings/{RULE}.yaml"
EVAL = f".codeguard/rule-evals/{RULE}.yaml"
GENERAL_RULE = (
    "# Knowledge stated once\n\nEach piece of knowledge has one home in the code.\n\n"
    "## Why\n\nTwo copies of one fact drift apart when only one is changed.\n"
)
BOTH_LANGUAGES = {"paths": ["**/*.py", "**/*.ts"], "triggers": ["string-literal"]}


def case(name: str, file: str, after: str, outcome: str = "invalid") -> dict[str, object]:
    return {
        "name": name,
        "inputs": {"file": file, "after": f"{after}\n"},
        "expected_output": {"outcome": outcome},
    }


PYTHON_CASE = case("a repeated status literal", "orders.py", 'STATUS = "shipped"')
TYPESCRIPT_CASE = case("a repeated status literal in a script", "orders.ts", "const s = 'shipped';")
