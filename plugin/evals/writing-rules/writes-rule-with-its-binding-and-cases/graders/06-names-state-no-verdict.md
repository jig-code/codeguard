---
type: llm
focus: { source: file, path: .codeguard/rule-evals/exception-handling.yaml }
weight: 1
---

This is a codeguard rule eval. Each case has a `name`, and its verdict is the `outcome` under `expected_output`.
PASS if no case's name states whether the case is valid, invalid or skipped.
FAIL if a case's name states the case's outcome.
