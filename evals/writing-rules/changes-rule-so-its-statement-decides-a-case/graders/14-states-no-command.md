---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-swallowed-exceptions.md }
weight: 1
---

PASS if the statement describes code and gives its reader no command. The statement is the sentence under this rule file's `#` title and before `## Why`, leaving out the title.
FAIL if the statement is missing or empty. Also FAIL if the statement is a command, such as a sentence that starts with "Flag", "Report", "Check" or "Never". Also FAIL if the statement addresses its reader, such as with "you".
