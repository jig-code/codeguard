---
type: llm
focus: last_message
weight: 1
---

The reply declines a codeguard judge rule because whether a function is called depends on the whole repository, which a judge can't decide from the changed file, and recommends an exact tool for it instead: a language server's find-references, or a dead-code tool such as vulture or a linter's unused-code check.
