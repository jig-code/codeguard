---
name: authoring-writing-rules
description: "Says what codeguard's writing-rules skill must be and how its evals test it. Use before writing, editing or reviewing anything under plugin/skills/writing-rules/ or plugin/evals/writing-rules/: the skill, its references, an eval case or a grader. Not for writing a codeguard rule."
---

# Authoring the writing-rules skill

The writing-rules skill, in `plugin/skills/writing-rules/`, is the guidance codeguard's
plugin gives an agent that writes or changes a codeguard rule. This skill is for changing
that skill and its evals.

- Before changing the skill or its references, read `references/authoring.md`. Every
  instruction in the skill traces to an item in it; an instruction that traces to none is
  removed.
- Before changing an eval case or a grader, or running the evals, read
  `references/testing.md`.
