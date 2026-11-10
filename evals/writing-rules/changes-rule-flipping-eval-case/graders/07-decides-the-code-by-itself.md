---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

The convention is the statement under the SKILL.md's title, before `## Why`. The frontmatter's `description` tells an agent what the skill is for and is not part of the convention.

PASS if the convention alone decides, for each piece of code it reads, whether that code keeps or breaks it.
FAIL if the convention alone doesn't decide whether some piece of code it reads keeps or breaks it.
