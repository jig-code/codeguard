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

Trace every instruction in the skill to an instruction below or to the `writing-skills`
skill, and remove one that traces to none.

- Agree with [codeguard's architecture](../../../docs/architecture.md#rules) and
  [Rule formats](../../../docs/rule-formats.md): never contradict them, and add only what
  an agent needs beyond them.
- Write the skill's `description` so the skill loads whenever someone asks for a
  codeguard rule to be written or changed.
- Keep everything the agent reads inside the skill. The agent works in another project,
  with the codeguard CLI and the skill, and none of codeguard's docs.
- Give no lists of words to match: a list decides only the words it names.
- Use only the words *keeps* and *breaks* for code against a rule.
- Say what a rule must be, in codeguard's public terms. Leave out how the judge reads a
  rule.
- Say that a rule uses plain, clear words that a developer new to the project the rule
  is for understands on the first read.
- Remove an instruction whose case passes in both arms of a with-without run, once what
  the agent wrote without the skill shows it follows that instruction unaided. Remove its
  case with it.

## Writing its evals

Before writing or changing an eval case or a grader, read `references/evals.md`.
