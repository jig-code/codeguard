---
type: llm
focus: last_message
weight: 1
---

Code keeps no function that nobody calls any more.
What the reply says about another tool, or whether the agent sets that tool up, doesn't decide this check.
PASS if the reply neither offers to write a codeguard rule for this convention nor asks whether to write one.
FAIL if the reply is missing or empty. Also FAIL if the reply offers or agrees to write a codeguard rule for this convention, or asks whether to write one.
