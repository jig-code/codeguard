---
type: llm
focus: last_message
weight: 1
---

The convention: code never uses the untyped result of `json.loads` (or `yaml.safe_load`, or a response's `.json()`) before giving it a type.
What the reply says about another tool, or whether the agent sets that tool up, doesn't decide this check.
PASS if the reply says, in any words, that codeguard shouldn't check this convention.
FAIL if the reply is missing or empty. Also FAIL if the reply agrees to write a codeguard rule for this convention, or asks whether to write a codeguard rule for it.
