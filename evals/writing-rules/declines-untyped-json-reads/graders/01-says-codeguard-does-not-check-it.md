---
type: llm
focus: last_message
weight: 1
---

PASS if the reply says that a codeguard rule should not check this convention.
FAIL if the reply is missing or empty. Also FAIL if the reply agrees to write the rule, or asks whether to write it. Also FAIL if the reply declines for another reason, such as a missing tool or a missing permission.
