---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
weight: 1
---

The statement is the text between this rule file's `#` title and its `## Why` heading. Judge only the statement: leave out the title and the `## Why` section.
PASS if no pronoun in the statement could mean more than one noun.
FAIL if the statement is missing or empty. Also FAIL if a pronoun in the statement could mean more than one noun.
