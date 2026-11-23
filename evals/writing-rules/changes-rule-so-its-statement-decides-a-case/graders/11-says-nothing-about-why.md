---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
weight: 1
---

PASS if the statement leaves out why the rule exists and what goes wrong when it's broken. The statement is the sentence under this rule file's `#` title and before `## Why`, leaving out the title.
FAIL if the statement is missing or empty. Also FAIL if the statement says why the rule exists or what goes wrong when it's broken.
