---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the sentence under this SKILL.md's `#` title and before `## Why`, leaving out the title and the frontmatter, states what the code that the sentence covers must never do.
FAIL if that sentence, leaving out the title and the frontmatter, is missing or empty, states what code must do instead of what that code must never do, or lists code shapes, values or names.
