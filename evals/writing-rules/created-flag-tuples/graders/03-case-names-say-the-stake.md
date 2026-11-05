---
type: llm
focus: { source: file, path: .codeguard/rule-evals/no-created-flag-results.yaml }
weight: 1
---

Every case in this rule eval has a name that says what is at stake: an invalid case's name says the harm the code causes, a valid case's name says what the code keeps safe, and a skipped case's name says what the edit leaves untouched. A name may say what the code does, as long as it also says that stake; a name that only says what the code does, or what shape it has, doesn't.
