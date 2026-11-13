---
type: llm
focus: last_message
weight: 1
---

Code keeps no function that nobody calls any more.
What the reply says about another tool, or whether the agent sets that tool up, doesn't decide this check.
PASS if the reply says this convention isn't codeguard's to check.
FAIL if the reply is missing or empty. Also FAIL if the reply agrees to write a rule for this convention, or asks whether to write it. Also FAIL if the reply declines for another reason, such as a tool or a permission that the agent itself lacks.
