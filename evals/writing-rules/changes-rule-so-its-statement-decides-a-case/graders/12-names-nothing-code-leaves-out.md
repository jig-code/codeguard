---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the statement names nothing that code leaves out. The statement is the sentence under this SKILL.md's `#` title and before `## Why`, leaving out the title and the frontmatter.
FAIL if the statement is missing or empty. Also FAIL if the statement has "without" followed by a verb, "fail to", "skip", or "leave" with "undone". Also FAIL if the statement names something else that code leaves out.
