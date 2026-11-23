---
type: llm
focus: { source: file, path: .codeguard/rules/judge/package-public-interface.md }
weight: 1
---

The statement is the sentence under this rule file's `#` title and before `## Why`, leaving out the title.
PASS if a developer reading only the statement would say that a package's own tests importing from its modules keep it.
FAIL if that developer would say those tests break it, or would have to guess.
