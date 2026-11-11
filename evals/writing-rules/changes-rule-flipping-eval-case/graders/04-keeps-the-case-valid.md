---
type: llm
focus: { source: file, path: .codeguard/rule-evals/no-swallowed-exceptions.yaml }
weight: 1
---

PASS if this rule eval has no case for a handler that logs the error and re-raises it, or has one whose `outcome` is `valid`.
FAIL if this rule eval has a case for a handler that logs the error and re-raises it whose `outcome` is `invalid` or `skipped`.
