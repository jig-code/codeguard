---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
weight: 1
---

PASS if the statement is a declarative sentence whose subject is the code it covers. The statement is the sentence under this rule file's `#` title and before `## Why`, leaving out the title.
FAIL if the statement is in the imperative mood.
