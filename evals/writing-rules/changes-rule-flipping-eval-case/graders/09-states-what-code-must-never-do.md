---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the sentence under this SKILL.md's `#` title and before `## Why`, leaving out the title and the frontmatter, states an intent.
FAIL if that sentence, leaving out the title and the frontmatter, is missing or empty, or lists the code shapes, steps or names code must use.
