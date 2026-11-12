---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the sentence under this SKILL.md's `#` title and before `## Why`, leaving out the title and the frontmatter, is written out in full: every relative pronoun that a phrase needs is in place, and every pronoun's noun is plain.
FAIL if that sentence, leaving out the title and the frontmatter, is missing or empty, drops a relative pronoun that a phrase needs, or has a pronoun whose noun is not plain.
