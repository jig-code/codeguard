---
type: llm
focus: {source: file, path: .codeguard/rule-evals/created-flag-results.yaml}
weight: 1
---

Every case name in this rule eval gives a reason, not only a description of the code:

- each `invalid` case's name says what goes wrong because of its code, such as what a caller has to do or gets wrong;
- each `valid` case's name says why its code keeps the rule;
- each `skipped` case's name says why the judge never sees it.

Grade only the names.
