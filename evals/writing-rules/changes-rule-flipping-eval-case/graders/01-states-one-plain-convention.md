---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

The convention is the statement under the SKILL.md's title, before `## Why`. The frontmatter's `description` tells an agent what the skill is for and is not part of the convention. A sentence or clause that restates the statement, gives its purpose or says what it ignores is a second statement. A declarative statement can say what code does ("An X does Y"), what it must do ("Every X must Y") or what it never does ("An X never does Y"); each form states the convention.

PASS if the convention is one declarative statement in words a reviewer would use, any sentence after it only fixes the meaning of a term in it a reader could take two ways and carries nothing that follows from that meaning, and that statement decides whether code keeps or breaks it.
FAIL if the convention holds a second statement or isn't declarative, uses a term nobody would use in a code review, is followed by a sentence that does more than fix the meaning of a term a reader could take two ways or that carries something that follows from that meaning, or doesn't by itself decide whether code keeps or breaks it.
