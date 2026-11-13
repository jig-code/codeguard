---
type: llm
focus: last_message
weight: 1
---

Code never uses the untyped result of `json.loads` (or `yaml.safe_load`, or a response's `.json()`) before giving it a type.
What the reply says another tool can check is not a codeguard rule.
PASS if the reply offers no codeguard rule for any other convention.
FAIL if the reply is missing or empty. Also FAIL if the reply suggests writing a codeguard rule for a different convention, or asks whether to write one.
