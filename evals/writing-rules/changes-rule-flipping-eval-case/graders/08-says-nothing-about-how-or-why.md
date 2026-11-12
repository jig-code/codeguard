---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the sentence under this SKILL.md's `#` title and before `## Why`, leaving out the title and the frontmatter, names no action that code must take to avoid what that code must never do, and states neither the harm the rule prevents nor any other why; a clause that only narrows what the sentence forbids is not an action.
FAIL if that sentence, leaving out the title and the frontmatter, is missing or empty, names an action that code must take to avoid what that code must never do, a ban on leaving that action undone among them, or states the harm the rule prevents or any other why.
