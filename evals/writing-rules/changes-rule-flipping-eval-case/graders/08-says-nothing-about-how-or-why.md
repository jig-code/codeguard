---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the sentence under this SKILL.md's `#` title and before `## Why`, leaving out the title and the frontmatter, names no action code must take to avoid what it must never do, and says nothing about why.
FAIL if that sentence, leaving out the title and the frontmatter, is missing or empty, names an action code must take to avoid what it must never do, a ban on skipping that action among them, or says why.
