---
type: llm
focus: { source: file, path: .codeguard/rule-evals/no-created-flag-results.yaml }
weight: 1
---

PASS if no two cases in this rule eval break or keep the convention on the same ground: each `invalid` case breaks it in a way no other does, and each `valid` case keeps it in a situation no other does.
FAIL if two `invalid` cases break the convention the same way, or two `valid` cases keep it in the same situation, differing only in syntax, names or annotations.
