---
type: llm
focus: { source: file, path: .codeguard/rules/judge/clear-log-messages.md }
weight: 1
---

The statement is the text between this rule file's `#` title and its `## Why` heading. Grade only the statement: leave out the title and the `## Why` section.
PASS if the statement says what code must never do.
FAIL if the statement is missing or empty. Also FAIL if the statement doesn't say what code must never do.
