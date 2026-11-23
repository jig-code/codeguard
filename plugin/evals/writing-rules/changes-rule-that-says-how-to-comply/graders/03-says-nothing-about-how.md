---
type: llm
focus: { source: file, path: .codeguard/rules/judge/defaults-on-the-type.md }
weight: 1
---

The statement is the sentence under this rule file's `#` title and before `## Why`, leaving out the title.
PASS if the statement describes only code that breaks the rule.
FAIL if the statement is missing or empty. Also FAIL if the statement also describes code that keeps the rule.
