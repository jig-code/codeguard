---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-swallowed-exceptions.md }
weight: 1
---

The statement is the text between this rule file's `#` title and its `## Why` heading. Grade only the statement, and read the `## Why` section only for the harm it names.
PASS if all code that does the harm that the `## Why` section names breaks the statement.
FAIL if the statement or the `## Why` section is missing or empty. Also FAIL if some code that does that harm keeps the statement.
