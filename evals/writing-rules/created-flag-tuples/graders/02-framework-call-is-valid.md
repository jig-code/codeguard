---
type: llm
focus: { source: file, path: .codeguard/rule-evals/no-created-flag-results.yaml }
weight: 1
---

This rule eval has a valid case in which code calls a framework's own get_or_create (or a similar idiomatic API that returns a created flag) and is expected to pass.
