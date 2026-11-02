---
type: llm
focus: { source: file, path: .codeguard/rule-evals/no-created-flag-results.yaml }
weight: 1
---

This rule eval has at most four invalid cases and at most four valid cases, and no two cases rest on the same ground: no two `reason` values say the same thing about the code, whatever the differences in syntax, names or annotations between their cases.
