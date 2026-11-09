---
type: llm
focus: { source: file, path: .codeguard/rule-evals/no-created-flag-results.yaml }
weight: 1
---

PASS if, in every case of this rule eval, every line other than the code the case tests is correct code a reviewer would accept.
FAIL if any case has a line that is wrong for a reason other than the one the case tests, such as a bug, an undefined name, or code that breaks a different convention.
