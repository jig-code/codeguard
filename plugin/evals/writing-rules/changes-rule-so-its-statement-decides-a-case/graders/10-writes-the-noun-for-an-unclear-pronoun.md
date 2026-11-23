---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
weight: 1
---

PASS if no pronoun in the statement could mean more than one noun. The statement is the sentence under this rule file's `#` title and before `## Why`, leaving out the title.
FAIL if a pronoun in the statement could mean more than one noun.
