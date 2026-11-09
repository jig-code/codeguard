---
type: llm
focus: { source: file, path: .codeguard/rule-evals/no-swallowed-exceptions.yaml }
weight: 1
---

The case 'logs the error and re-raises' in this rule eval is either removed or kept as a clearly valid case (a handler that logs the exception and re-raises it), not reworded into a borderline one.
