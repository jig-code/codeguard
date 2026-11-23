---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
weight: 1
---

PASS if the statement uses only common words. The statement is the sentence under this rule file's `#` title and before `## Why`, leaving out the title.
FAIL if the statement uses a made-up term or a name only this project uses.
