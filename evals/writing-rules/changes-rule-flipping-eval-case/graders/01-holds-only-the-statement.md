---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

The convention is only the statement's sentence under the SKILL.md's title, before `## Why`. The title and the frontmatter's `description` name the rule and are not part of the convention.

PASS if the convention says what code must do or never do, once, and nothing about how code does it or why.
FAIL if the convention says what code must do or never do more than once, or a sentence or clause in it says how code does it or why.
