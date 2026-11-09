---
type: llm
focus: { source: file, path: .codeguard/skills/no-created-flag-results/SKILL.md }
weight: 1
---

PASS if this SKILL.md has a `## Why` section that states, in one or two sentences, the harm the rule prevents, and the section names no code the convention's statement doesn't decide.
FAIL if not: for example there is no `## Why` section, it runs longer than two sentences, it only restates the convention or states a benefit instead of a harm, or it widens the convention.
