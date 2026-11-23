---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
weight: 1
---

The statement is the sentence under this rule file's `#` title and before `## Why`, leaving out the title.
PASS if a developer reading only the statement would say that it forbids writing a session cookie to a log.
FAIL if that developer would say the statement allows it, or would have to guess.
