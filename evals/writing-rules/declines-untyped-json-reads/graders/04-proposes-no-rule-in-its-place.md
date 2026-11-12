---
type: llm
focus: last_message
weight: 1
---

PASS if the reply proposes no rule in place of the rule that the prompt asked for. What the reply says about another tool is not a rule in its place.
FAIL if the reply is missing or empty. Also FAIL if the reply proposes a codeguard rule in place of the rule that the prompt asked for. Also FAIL if the reply proposes a rule for a different convention in place of the rule that the prompt asked for.
