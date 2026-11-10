---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

PASS if the text between this SKILL.md's title and its first `##` section is one sentence.
FAIL if that text holds more than one sentence, or holds a list or other text that isn't a sentence.
