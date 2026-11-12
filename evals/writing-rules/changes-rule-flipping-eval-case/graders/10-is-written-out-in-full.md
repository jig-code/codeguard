---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the sentence under this SKILL.md's `#` title and before `## Why`, leaving out the title and the frontmatter, is written out in full: no relative pronoun is dropped where a phrase could misparse, and no pronoun's noun is unclear.
FAIL if that sentence, leaving out the title and the frontmatter, is missing or empty, drops a relative pronoun where a phrase could misparse, or has a pronoun whose noun is unclear.
