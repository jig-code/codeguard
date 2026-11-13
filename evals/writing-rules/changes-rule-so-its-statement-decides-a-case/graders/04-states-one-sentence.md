---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the text is one sentence. The text is everything under this SKILL.md's `#` title and before its first `##` section, leaving out the title and the frontmatter.
FAIL if the text is missing or empty. Also FAIL if the text runs to a second sentence. Also FAIL if the text is a list.
