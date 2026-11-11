---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the text under this SKILL.md's `#` title and before its first `##` section, leaving out the title and the frontmatter, is one sentence.
FAIL if that text, leaving out the title and the frontmatter, is missing or empty, runs to a second sentence, or is a list.
