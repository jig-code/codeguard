---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
weight: 1
---

The statement is the text between this rule file's `#` title and its `## Why` heading. Grade only the statement: leave out the title and the `## Why` section.
PASS if the statement names what all the code that breaks the rule has in common, and names no particular things that code does or uses. A particular thing is something that only some of the code that breaks the rule does or uses. A clause that describes more precisely what all that code has in common is part of the statement.
FAIL if the statement is missing or empty. Also FAIL if the statement names one or more particular things that code does or uses, whether instead of or alongside what that code has in common.
