---
type: llm
focus: { source: file, path: .codeguard/rule-evals/no-created-flag-results.yaml }
weight: 1
---

PASS if each `invalid` case's name states a harm the rule prevents, each `valid` case's name states the situation in which its code keeps the convention, and each `skipped` case's name states what the edit leaves untouched.
FAIL if any case's name instead describes what its code does or its shape, such as the call it makes or the type it returns, or if an `invalid` case's name states no harm.
