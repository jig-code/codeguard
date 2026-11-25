---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
weight: 1
---

The statement is the sentence under this rule file's `#` title and before `## Why`, leaving out the title.
PASS if the statement says what code must never do.
FAIL if the statement is missing or empty. Also FAIL if the statement doesn't say what code must never do.
