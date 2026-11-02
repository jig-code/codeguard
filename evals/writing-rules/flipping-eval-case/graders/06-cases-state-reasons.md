---
type: llm
focus: { source: file, path: .codeguard/rule-evals/no-swallowed-exceptions.yaml }
weight: 1
---

Every case whose outcome is invalid or valid has a `reason` under expected_output, one sentence naming the code and what it does or fails to do, and no skipped case has one. (A case with no `reason` or a `reason` that only restates the outcome fails this.)
