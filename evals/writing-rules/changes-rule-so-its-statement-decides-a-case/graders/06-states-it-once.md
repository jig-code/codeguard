---
type: llm
focus: { source: file, path: .codeguard/rules/judge/no-swallowed-exceptions.md }
weight: 1
---

PASS if the statement says its requirement once. The statement is the sentence under this rule file's `#` title and before `## Why`, leaving out the title.
FAIL if the statement is missing or empty. Also FAIL if the statement says its requirement a second time, in other words or in the negative.
