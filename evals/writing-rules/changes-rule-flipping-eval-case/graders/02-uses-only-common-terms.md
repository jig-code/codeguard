---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the text between this SKILL.md's title and `## Why` uses only common terms and no term the agent invented.
FAIL if the text between this SKILL.md's title and `## Why` uses a term the agent invented.
