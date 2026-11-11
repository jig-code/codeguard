---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the text between this SKILL.md's title and `## Why` says nothing about how code meets its requirement or why.
FAIL if that text is missing or empty, or has a clause naming the steps or mechanism code uses to meet the requirement, or a clause giving the requirement's reason or consequence.
