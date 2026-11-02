---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

Under this SKILL.md's wording, catching Exception or using a bare except is not a violation by itself: a handler that catches broadly and re-raises keeps the convention. The convention no longer lists the broad catch as a form that breaks it (the text may still say the type caught doesn't matter).
