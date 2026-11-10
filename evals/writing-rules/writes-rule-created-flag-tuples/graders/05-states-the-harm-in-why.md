---
type: llm
focus: { source: file, path: .codeguard/skills/no-created-flag-results/SKILL.md }
weight: 1
---

PASS if this SKILL.md has a `## Why` section that states, in one or two sentences, the harm the rule prevents and not its fix, and the section names no code the convention's statement doesn't decide.
FAIL if this SKILL.md has no `## Why` section, or that section runs longer than two sentences, doesn't state a harm the rule prevents, proposes a fix or a different design, or names code the convention's statement doesn't decide.
