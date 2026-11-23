---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
weight: 1
---

The statement is the sentence under this rule file's `#` title and before `## Why`, leaving out the title.
The case to judge writes a session cookie to a log.
PASS if a reader of the statement alone can tell whether that case keeps or breaks the statement.
FAIL if the statement is missing or empty. Also FAIL if one part of the statement flags that case and another part allows it. Also FAIL if the statement neither flags nor allows that case.
