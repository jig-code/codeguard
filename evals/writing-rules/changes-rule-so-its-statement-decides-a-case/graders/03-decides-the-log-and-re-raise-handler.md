---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-swallowed-exceptions.md }
weight: 1
---

The statement is the sentence under this rule file's `#` title and before `## Why`, leaving out the title.
The handler to judge catches `Exception`, logs the error, and then re-raises it.
PASS if a reader of the statement alone can tell whether that handler keeps or breaks the statement.
FAIL if the statement is missing or empty. Also FAIL if one part of the statement flags that handler and another part allows it. Also FAIL if the statement neither flags nor allows that handler.
