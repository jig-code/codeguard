---
type: llm
focus: { source: file, path: .codeguard/rule-evals/no-created-flag-results.yaml }
weight: 1
---

This rule eval has at most four invalid and at most four valid cases, and no two cases rest on the same ground: no two `reason` values say the same thing about what the code does or fails to do, whatever the differences in syntax, names or annotations between their cases. One invalid case is enough when the convention can be broken in one way.
