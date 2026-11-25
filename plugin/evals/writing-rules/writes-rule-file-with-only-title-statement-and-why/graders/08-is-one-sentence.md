---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
weight: 1
---

The statement is the text between this rule file's `#` title and its `## Why` heading. Judge only the statement: leave out the title and the `## Why` section.
PASS if the statement is one sentence.
FAIL if the statement is missing or empty. Also FAIL if the statement runs to a second sentence. Also FAIL if the statement is a list.
