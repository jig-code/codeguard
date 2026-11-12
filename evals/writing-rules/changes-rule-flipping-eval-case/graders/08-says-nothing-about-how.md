---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the statement names no action that code must take to avoid what that code must never do. A clause that only narrows what the statement forbids is not an action. The statement is the sentence under this SKILL.md's `#` title and before `## Why`, leaving out the title and the frontmatter.
FAIL if the statement is missing or empty. Also FAIL if the statement names an action that code must take to avoid what that code must never do.
