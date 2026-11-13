---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

The statement is the sentence under this SKILL.md's `#` title and before `## Why`, leaving out the title and the frontmatter.
The handler to judge catches `Exception`, logs the error, and then re-raises it.
PASS if a reader of the statement alone can tell whether that handler keeps or breaks the statement.
FAIL if the statement is missing or empty. Also FAIL if one part of the statement flags that handler and another part allows it.
