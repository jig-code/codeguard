---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

The convention is the statement under the SKILL.md's title, before `## Why`. The frontmatter's `description` tells an agent what the skill is for and is not part of the convention.

PASS if the convention says what code must do or never do, once, and nothing about how code does it or why.
FAIL if the convention says what code must do or never do more than once, or a sentence or clause in it says how code does it or why.
