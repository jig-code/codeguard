---
type: llm
focus: { source: file, path: .codeguard/rule-evals/no-created-flag-results.yaml }
weight: 1
---

Every case name in this rule eval reads as the ground of its verdict, why the code is a problem or why it is fine, rather than as a description of what the code does or what the edit changes. Judge each name on its own; one name that only describes the code fails this.
