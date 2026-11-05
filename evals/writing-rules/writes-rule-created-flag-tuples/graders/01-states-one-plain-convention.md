---
type: llm
focus: { source: file, path: .codeguard/skills/no-created-flag-results/SKILL.md }
weight: 1
---

PASS if this SKILL.md states its convention as one declarative statement in words a reviewer would use, followed at most by one sentence that fixes the meaning of a term in it a reader could take two ways, and the convention's statement alone decides whether code keeps or breaks it.
FAIL if the convention is a question, holds a second statement (another sentence, or a clause joined to the first by a semicolon, a dash or a conjunction, that adds a requirement or restates the first in other words, such as its negation), uses a term nobody would use in a code review, or is a list of code shapes, values or names instead of a statement.
