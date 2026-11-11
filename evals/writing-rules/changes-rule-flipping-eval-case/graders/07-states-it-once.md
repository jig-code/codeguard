---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the sentence under this SKILL.md's `#` title and before `## Why`, leaving out the title and the frontmatter, says its requirement once.
FAIL if that sentence, leaving out the title and the frontmatter, is missing or empty, or says its requirement a second time, in other words or in the negative.
