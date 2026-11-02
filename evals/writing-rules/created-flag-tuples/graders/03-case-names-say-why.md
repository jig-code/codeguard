---
type: llm
focus: { source: file, path: .codeguard/rule-evals/no-created-flag-results.yaml }
weight: 1
---

Every case name in this rule eval says what is at stake: for an invalid case the harm the code does (to its callers, readers or the design), for a valid case what the code keeps safe. A name that describes the code's action or shape (what it returns, calls, builds, adds or edits) fails this; judge each name on its own, and one such name fails the grader.
