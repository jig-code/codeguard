---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

The convention is the statement under the SKILL.md's title, before `## Why`. The frontmatter's `description` tells an agent what the skill is for and is not part of the convention. A sentence or clause that defines a term in the statement, restates it, gives its purpose or says what it ignores is a second statement. A declarative statement can say what code does ("An X does Y"), what it must do ("Every X must Y") or what it never does ("An X never does Y"); each form states the convention.

PASS if the convention is one declarative statement in words a reviewer would use, with no sentence after it, and that statement decides whether code keeps or breaks it.
FAIL if the convention holds a second statement or isn't declarative, uses a term nobody would use in a code review, is followed by another sentence, or doesn't by itself decide whether code keeps or breaks it.
