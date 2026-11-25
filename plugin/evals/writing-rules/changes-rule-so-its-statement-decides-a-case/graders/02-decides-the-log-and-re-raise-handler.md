---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-swallowed-exceptions.md }
weight: 1
---

The statement is the sentence under this rule file's `#` title and before `## Why`, leaving out the title.
The handler to judge catches `Exception`, logs the error, and then re-raises it.
PASS if a reader of the statement alone can tell that the handler keeps the statement.
FAIL if the statement is missing or empty. Also FAIL if the statement forbids that handler. Also FAIL if a reader of the statement alone can't tell whether that handler keeps or breaks the statement.
