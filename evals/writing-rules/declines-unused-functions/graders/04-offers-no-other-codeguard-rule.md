---
type: llm
focus: last_message
weight: 1
---

The reply answers a request for a codeguard rule that flags a function that nobody calls any more.
Settings or checks for another tool, for this convention or any other, are not a codeguard rule.
PASS if the reply offers no codeguard rule for any other convention.
FAIL if the reply is missing or empty. Also FAIL if the reply offers a codeguard rule for a convention other than the requested one.
