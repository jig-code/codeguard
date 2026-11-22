---
type: llm
focus: last_message
weight: 1
---

The agent was asked for a codeguard rule for this convention: code never uses the untyped result of `json.loads` (or `yaml.safe_load`, or a response's `.json()`) before giving it a type.
What the reply says about another tool, or whether the agent sets that tool up, doesn't decide this check.
PASS if the reply says, in any words, that codeguard shouldn't check this convention because an exact tool or a search of the repository can decide it.
FAIL if the reply is missing or empty. Also FAIL if the reply agrees to write a codeguard rule for this convention, or asks whether to write one.
