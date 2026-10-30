---
type: llm
focus: {source: file, path: .codeguard/rule-evals/created-flag-results.yaml}
weight: 1
---

This rule eval has a `valid` case and an `invalid` case whose `after` code makes the same library call or uses the same construct, such as both calling an ORM's get_or_create: the `valid` case uses it in a way the convention allows, and the `invalid` case uses it in a way that breaks the convention. Grade only whether such a pair exists.
