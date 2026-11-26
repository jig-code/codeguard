---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
weight: 1
---

The statement is the text between this rule file's `#` title and its `## Why` heading. Grade only the statement, and read the `## Why` section only for the harm it names.
PASS if no code that the statement says keeps the rule does the harm that the `## Why` section names.
FAIL if the statement or the `## Why` section is missing or empty. Also FAIL if some code that the statement says keeps the rule does the harm that the `## Why` section names.
