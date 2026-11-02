---
type: llm
focus: {source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md}
weight: 1
---

This SKILL.md no longer treats catching Exception or a bare except as a violation in itself: that form, which contradicts not swallowing when the clause re-raises, is removed from this rule.
