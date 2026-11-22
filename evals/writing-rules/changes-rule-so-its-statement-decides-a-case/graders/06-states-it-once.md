---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
weight: 1
---

The statement is the line of text after the rule file's title.
PASS if no clause of the statement forbids again what another clause of it already forbids.
FAIL if the statement is missing or empty. Also FAIL if one clause of the statement forbids again what another clause of it already forbids.
