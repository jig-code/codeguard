---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if every term in the text between this SKILL.md's title and `## Why` is one a reviewer would use in a code review.
FAIL if the text between this SKILL.md's title and `## Why` uses a term nobody would use in a code review.
