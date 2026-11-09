---
type: llm
focus: { source: file, path: .codeguard/rule-evals/no-created-flag-results.yaml }
weight: 1
---

PASS if this rule eval has a case expected `valid` whose code calls a framework's own API that returns a created flag, such as Django's get_or_create, whether the code uses the flag or discards it.
FAIL if no case calls such an API, or every case that calls one is expected `invalid` or `skipped`.
