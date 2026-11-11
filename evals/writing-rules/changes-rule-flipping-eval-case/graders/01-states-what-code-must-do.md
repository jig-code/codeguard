---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the text between this SKILL.md's title and `## Why` states what code must do or never do.
FAIL if that text is missing or empty, is a question, or describes code without saying what it must or must not do.
