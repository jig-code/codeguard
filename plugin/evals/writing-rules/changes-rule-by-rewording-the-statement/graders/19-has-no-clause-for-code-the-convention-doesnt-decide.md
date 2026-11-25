---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-swallowed-exceptions.md }
weight: 1
---

The statement is the text between this rule file's `#` title and its `## Why` heading. Grade only the statement: leave out the title and the `## Why` section.
PASS if the statement has no clause for code that the rest of the statement doesn't decide. A clause that only narrows what the statement forbids is part of the convention.
FAIL if the statement is missing or empty. Also FAIL if the statement has a clause for code that the rest of the statement doesn't decide.
