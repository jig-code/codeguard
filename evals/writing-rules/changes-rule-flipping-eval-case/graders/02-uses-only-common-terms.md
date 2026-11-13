---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the statement uses no term that its author invented, such as a made-up word or a name that only this project uses. The statement is the sentence under this SKILL.md's `#` title and before `## Why`, leaving out the title and the frontmatter.
FAIL if the statement is missing or empty. Also FAIL if the statement uses a term that its author invented, such as a made-up word or a name that only this project uses.
