---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

The convention is the statement under the SKILL.md's title, before `## Why`. The frontmatter's `description` tells an agent what the skill is for and is not part of the convention.

PASS if every term in the convention is one a reviewer would use in a code review.
FAIL if the convention uses a term nobody would use in a code review.
