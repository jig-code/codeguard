---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

What the requirement asks code to do, and any condition that decides which code it covers, is part of the requirement, not how code meets it.

PASS if the text between this SKILL.md's title and `## Why` says nothing about how code meets its requirement or why.
FAIL if that text is missing or empty, or has a clause naming the steps or mechanism code uses to meet the requirement, or a clause giving the requirement's reason or consequence.
