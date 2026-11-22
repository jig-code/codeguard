---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
weight: 1
---

The statement is the line of text after the rule file's title.
PASS if the statement forbids one behaviour without listing code shapes, values or names.
FAIL if the statement is missing or empty. Also FAIL if the statement lists two or more code shapes, values or names that it forbids.
