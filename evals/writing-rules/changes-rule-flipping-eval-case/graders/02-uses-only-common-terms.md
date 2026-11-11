---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the sentence under this SKILL.md's `#` title and before `## Why`, leaving out the title and the frontmatter, uses only common terms and no term the agent invented.
FAIL if that sentence, leaving out the title and the frontmatter, is missing or empty, or uses a term the agent invented.
