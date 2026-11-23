---
type: llm
focus: { source: file, path: .codeguard/rules/judge/defaults-on-the-type.md }
weight: 1
---

The statement is the sentence under this rule file's `#` title and before `## Why`, leaving out the title.
PASS if a developer reading only the statement would say that a call passing a function parameter's default value again breaks it.
FAIL if that developer would say that call keeps it, or would have to guess.
