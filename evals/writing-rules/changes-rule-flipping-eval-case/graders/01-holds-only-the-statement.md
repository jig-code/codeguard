---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

The convention is the statement under the SKILL.md's title, before `## Why`. The frontmatter's `description` tells an agent what the skill is for and is not part of the convention.

PASS if the convention is its one statement, with no other sentence or clause beside it.
FAIL if the convention holds a sentence or clause beside its one statement.
