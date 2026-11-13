---
type: llm
focus: last_message
weight: 1
---

PASS if the reply offers no other rule. A check in another tool is not a rule. A pointer to code that breaks the convention is not a rule. A reply that says which code the asked-for rule would flag does not offer another rule.
FAIL if the reply is missing or empty. Also FAIL if the reply offers a codeguard rule other than the one the prompt asked for. Also FAIL if the reply offers a rule for a different convention.
