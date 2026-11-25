---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
weight: 1
---

PASS if a developer new to the project understands every term in the statement on the first read. The statement is the sentence under this rule file's `#` title and before `## Why`, leaving out the title.
FAIL if the statement is missing or empty. Also FAIL if the statement uses a term that its author made up, or a term that only the project's own code or docs define.
