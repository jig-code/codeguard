---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the text between this SKILL.md's title and its first `##` section is one sentence.
FAIL if that text is missing or empty, runs to a second sentence, or is a list.
