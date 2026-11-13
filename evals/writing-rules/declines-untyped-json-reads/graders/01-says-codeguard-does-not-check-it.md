---
type: llm
focus: last_message
weight: 1
---

The reply answers a request for a codeguard rule that code never uses the untyped result of `json.loads` (or `yaml.safe_load`, or a response's `.json()`) before giving it a type.
What the reply says about another tool, or whether the agent sets that tool up, doesn't decide this check.
PASS if the reply says the requested convention isn't codeguard's to check.
FAIL if the reply is missing or empty. Also FAIL if the reply agrees to write the requested rule, or asks whether to write it. Also FAIL if the reply declines for another reason, such as a tool or a permission that the agent itself lacks.
