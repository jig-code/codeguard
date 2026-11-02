---
type: llm
focus: { source: file, path: .codeguard/rule-evals/no-created-flag-results.yaml }
weight: 1
---

Each case name is written from the point of view of the code's callers or readers: what they are made to do or can't rely on (invalid), or what they can rely on (valid, skipped). A name that merely describes the function's action or shape, with no caller or reader in it, fails. Judge each name on its own; one failing name fails the grader.
