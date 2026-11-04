---
type: llm
focus: { source: file, path: .codeguard/rule-evals/no-created-flag-results.yaml }
weight: 1
---

PASS if every case's name in this rule eval says what is at stake: for an `invalid` case the harm, for a `valid` case what the code keeps safe, and for a `skipped` case what the edit leaves untouched.
FAIL if any case's name describes what the code does or its shape, such as the call it makes or the type it returns, instead of what is at stake.
