---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
weight: 1
---

The statement is the sentence under this rule file's `#` title and before `## Why`, leaving out the title.
PASS if the statement names what all the code that breaks the rule has in common. A clause that only narrows that is part of it.
FAIL if the statement is missing or empty. Also FAIL if the statement names one or more particular things instead of what they have in common.
