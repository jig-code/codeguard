---
type: llm
focus: { source: file, path: .codeguard/skills/no-created-flag-results/SKILL.md }
weight: 1
---

PASS if this SKILL.md has a `## Why` section that states, in one or two sentences, the harm the rule prevents, and the section doesn't widen the convention.
FAIL if there is no `## Why` section, the section is longer than two sentences, it states no harm (it only restates the convention), or it names code the convention's statement doesn't decide.
