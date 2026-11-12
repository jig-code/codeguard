---
type: llm
focus: { source: file, path: .codeguard/rule-evals/no-swallowed-exceptions.yaml }
weight: 1
---

PASS if this rule eval has no case for a handler that logs the error and re-raises it. Also PASS if the rule eval's case for a handler that logs the error and re-raises it has an `outcome` of `valid`.
FAIL if this rule eval is missing or empty. Also FAIL if the case for a handler that logs the error and re-raises it has an `outcome` of `invalid` or `skipped`.
