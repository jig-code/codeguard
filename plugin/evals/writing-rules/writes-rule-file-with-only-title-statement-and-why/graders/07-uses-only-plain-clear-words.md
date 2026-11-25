---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
weight: 1
---

The statement is the text between this rule file's `#` title and its `## Why` heading. Judge only the statement: leave out the title and the `## Why` section.
PASS if a developer new to the project understands every word of the statement on the first read.
FAIL if the statement is missing or empty. Also FAIL if the statement uses a word that a developer new to the project would not understand on the first read.
