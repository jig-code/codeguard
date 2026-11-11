---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the text between this SKILL.md's title and `## Why` says its requirement once.
FAIL if that text is missing or empty, or says its requirement a second time, in other words or in the negative.
