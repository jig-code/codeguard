---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the text under this SKILL.md's `#` title and before its first `##` section is one sentence. That text leaves out the title and the frontmatter.
FAIL if that text is missing or empty. Also FAIL if that text runs to a second sentence. Also FAIL if that text is a list.
