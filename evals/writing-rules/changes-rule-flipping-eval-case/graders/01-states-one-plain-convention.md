---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

The convention is the statement under the SKILL.md's title, before `## Why`. The frontmatter's `description` tells an agent what the skill is for and is not part of the convention. A clause belongs to the statement when removing it would change which code keeps or breaks the convention; a clause whose removal changes nothing is a second statement. A declarative statement can say what code does ("An X does Y") or what it must do ("Every X must Y"); either form states the convention.

PASS if the convention is one declarative statement in words a reviewer would use, any sentence after it only fixes the meaning of a term in it a reader could take two ways, and that statement decides whether code keeps or breaks it.
FAIL if not: for example the convention holds a second statement, a sentence after it does more than fix a term, it uses a term nobody would use in a code review, or it points at a list of code shapes instead of deciding them.
