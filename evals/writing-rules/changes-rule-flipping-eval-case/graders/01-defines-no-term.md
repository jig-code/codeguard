---
type: llm
focus: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
weight: 1
---

The convention is the statement under the SKILL.md's title, before `## Why`. The frontmatter's `description` tells an agent what the skill is for and is not part of the convention. A declarative statement can say what code does ("An X does Y"), what it must do ("Every X must Y") or what it never does ("An X never does Y"); each form states the convention.

PASS if the convention is one declarative statement, and no sentence or clause in it defines a term in the statement, restates the statement, gives its purpose or says what it ignores.
FAIL if the convention isn't declarative, holds more than one statement, or holds a sentence or clause that defines a term in the statement, restates the statement, gives its purpose or says what it ignores.
