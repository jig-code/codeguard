---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
weight: 1
---

The statement is the line of text after the rule file's title.
PASS if the statement uses no term that its author invented, such as a made-up word or a name that only this project uses.
FAIL if the statement is missing or empty. Also FAIL if the statement uses a term that its author invented, such as a made-up word or a name that only this project uses.
