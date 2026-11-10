---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the text between this SKILL.md's title and its first `##` section is at most two sentences: the convention, and at most one sentence after it that fixes the meaning of a term in it.
FAIL if not: for example that text holds three sentences or more, or a list.
