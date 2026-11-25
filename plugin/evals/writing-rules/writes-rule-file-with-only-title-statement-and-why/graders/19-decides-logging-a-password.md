---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
weight: 1
---

The statement is the sentence under this rule file's `#` title and before `## Why`, leaving out the title.
The code to judge writes a user's password to a log.
PASS if a reader of the statement alone can tell that the code breaks the statement.
FAIL if the statement is missing or empty. Also FAIL if the statement allows that code. Also FAIL if a reader of the statement alone can't tell whether that code keeps or breaks the statement.
