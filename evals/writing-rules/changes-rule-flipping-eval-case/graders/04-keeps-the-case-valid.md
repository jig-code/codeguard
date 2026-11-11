---
type: llm
focus: { source: file, path: .codeguard/rule-evals/no-swallowed-exceptions.yaml }
weight: 1
---

PASS if this rule eval has no case for a handler that logs the error and re-raises it, or a reader of that case alone sees, beyond argument, why its code gets the outcome the case expects.
FAIL if this rule eval has a case for a handler that logs the error and re-raises it, and a reader of that case alone could argue that its code gets an outcome other than the one the case expects.
