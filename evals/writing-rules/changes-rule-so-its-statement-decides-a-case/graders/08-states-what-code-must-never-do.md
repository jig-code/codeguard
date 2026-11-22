---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
weight: 1
---

The statement is the line of text after the rule file's title.
PASS if the statement states what the code that the statement covers must never do.
FAIL if the statement is missing or empty. Also FAIL if the statement states what code must do instead of what that code must never do.
