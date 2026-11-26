---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-swallowed-exceptions.md }
weight: 1
---

The statement is the text between this rule file's `#` title and its `## Why` heading. Grade only the statement: leave out the title and the `## Why` section.
PASS if the statement names what all the code that breaks the rule has in common. A clause that describes more precisely what that code has in common is part of the statement.
FAIL if the statement is missing or empty. Also FAIL if the statement names one or more particular things instead of what they have in common.
