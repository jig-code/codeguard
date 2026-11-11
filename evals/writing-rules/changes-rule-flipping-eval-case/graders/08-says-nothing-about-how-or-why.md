---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the sentence under this SKILL.md's `#` title and before `## Why`, leaving out the title and the frontmatter, says nothing about how code meets its requirement or why.
FAIL if that sentence, leaving out the title and the frontmatter, is missing or empty, or has a clause naming the steps or mechanism code uses to meet the requirement, or a clause giving the requirement's reason or consequence.
