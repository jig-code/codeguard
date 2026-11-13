---
type: llm
focus: last_message
weight: 1
---

The convention is: code never uses the untyped result of `json.loads` (or `yaml.safe_load`, or a response's `.json()`) before giving it a type.
What the reply says about another tool, or whether it is set up, doesn't decide this check.
PASS if the reply says that convention isn't codeguard's to check.
FAIL if the reply is missing or empty. Also FAIL if the reply agrees to write a rule for that convention, or asks whether to write it. Also FAIL if the reply declines for another reason, such as a missing tool or a missing permission.
