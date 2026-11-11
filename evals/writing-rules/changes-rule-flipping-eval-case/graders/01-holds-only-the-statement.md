---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the text between this SKILL.md's title and `## Why` says what code must do or never do, once, and nothing about how code does it or why.
FAIL if the text between this SKILL.md's title and `## Why` says what code must do or never do more than once, or holds a sentence or clause that says how code does it or why.
