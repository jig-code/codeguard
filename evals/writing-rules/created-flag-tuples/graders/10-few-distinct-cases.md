---
type: llm
focus: { source: file, path: .codeguard/rule-evals/no-created-flag-results.yaml }
weight: 1
---

The rule eval has at most four invalid and at most four valid cases, and each case tests something no other case does: a different thing the code does or fails to do, not another syntax for the same thing.
