---
type: llm
focus: { source: file, path: .codeguard/skills/no-created-flag-results/SKILL.md }
weight: 1
---

The convention is the statement under the SKILL.md's title, before `## Why`. The frontmatter's `description` tells an agent what the skill is for and is not part of the convention.

PASS if the convention is one declarative statement in words a reviewer would use, followed at most by one sentence that fixes the meaning of a term in it a reader could take two ways, and that statement alone decides whether code keeps or breaks it. One statement may offer alternatives, or set what it requires against what it rules out.
FAIL if the convention is a question, holds a second statement (another sentence, or a joined clause that adds a separate requirement or says again in other words what the statement already says), uses a term nobody would use in a code review, or is a list of code shapes, values or names instead of a statement.
