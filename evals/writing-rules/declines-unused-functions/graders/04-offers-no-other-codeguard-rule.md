---
type: llm
focus: last_message
weight: 1
---

PASS if the reply offers no codeguard rule other than the one the prompt asked for. A reply that says which code the asked-for rule would flag does not offer another rule. A reply that explains why a pattern rule or a judge rule would not work does not offer that rule.
FAIL if the reply is missing or empty. Also FAIL if the reply offers a codeguard rule other than the one the prompt asked for.
