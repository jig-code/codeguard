---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-swallowed-exceptions.md }
weight: 1
---

The statement is the text between this rule file's `#` title and its `## Why` heading. Judge only the statement: leave out the title and the `## Why` section.
PASS if the statement says nothing it forbids a second time.
FAIL if the statement is missing or empty. Also FAIL if the statement says something it forbids a second time, in other words or as what code must do instead.
