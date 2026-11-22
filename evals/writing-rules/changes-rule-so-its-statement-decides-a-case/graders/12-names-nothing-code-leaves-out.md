---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
weight: 1
---

The statement is the line of text after the rule file's title.
PASS if the statement names nothing that code leaves out.
FAIL if the statement is missing or empty. Also FAIL if the statement names something that code leaves out.
