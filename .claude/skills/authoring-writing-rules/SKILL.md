---
name: authoring-writing-rules
description: "Says what codeguard's writing-rules skill must be and how to write its evals. Use before writing, editing or reviewing anything under plugin/skills/writing-rules/ or plugin/evals/writing-rules/: the skill, its references, an eval case or a grader."
---

# Authoring the writing-rules skill

The writing-rules skill, in `plugin/skills/writing-rules/`, guides an agent that writes or
changes a codeguard rule. Use this skill to change that skill or its evals. Below, "the
skill" means the writing-rules skill.

First, load the `writing-skills` skill: it says how to write any skill, and this skill
adds only what is particular to the writing-rules skill.

## Writing the skill

- Make sure nothing in the skill contradicts
  [codeguard's architecture](../../../docs/architecture.md#rules) or
  [Rule formats](../../../docs/rule-formats.md).
- Write the skill's `description` so the skill loads whenever someone asks for a
  codeguard rule to be written or changed.
- Point the agent only to the skill's own files and the files of the project it works in.
  The agent has the codeguard CLI, the skill and that project, and can open none of
  codeguard's docs or code.
- Give no lists of words to match: a list decides only the words it names.
- Use only the words *keeps* and *breaks* for code against a rule.
- Say what a rule must be, in codeguard's public terms. Leave out how the judge reads a
  rule.
- Say that a rule uses plain, clear words that a developer new to the project the rule
  is for understands on the first read.
- Remove an instruction when the runs without the skill show that the agent follows the
  instruction. They show it when every grader that checks the instruction passes and the
  agent's output follows the instruction. Remove those graders, and any case that tests
  the instruction.

## Writing its evals

Before writing or changing an eval case or a grader, read `references/evals.md`.
