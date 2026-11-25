---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
weight: 1
---

The statement is the text between this rule file's `#` title and its `## Why` heading. Grade only the statement: leave out the title and the `## Why` section.
PASS if the statement states one convention and has no clause for code that the convention doesn't decide.
FAIL if the statement is missing or empty. Also FAIL if the statement states two or more conventions, so that code could keep one of them and break another. Also FAIL if a clause of the statement allows or forbids code that the rest of the statement doesn't decide.
