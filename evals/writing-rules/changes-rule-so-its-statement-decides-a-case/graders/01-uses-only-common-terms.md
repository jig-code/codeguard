---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
weight: 1
---

PASS if the statement uses no term that its author invented, such as a made-up word or a name that only this project uses. The statement is the sentence under this rule file's `#` title and before `## Why`, leaving out the title.
FAIL if the statement is missing or empty. Also FAIL if the statement uses a term that its author invented, such as a made-up word or a name that only this project uses.
