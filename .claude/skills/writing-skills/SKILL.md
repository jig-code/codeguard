---
name: writing-skills
description: "Says how to write a skill in this repository. Use it whenever you change any skill's SKILL.md, description or reference files, under .claude/skills/ or plugin/skills/, even for a small edit. Use it alongside skill-creator; where they differ, follow this skill."
---

# Writing a skill

Below, "the agent" means the agent that will use the skill you are writing.

- Write the skill's `description` so the skill loads whenever someone asks, in their own
  words, for the task it covers.
- Write only what the agent wouldn't know or do unaided. Leave out what it can learn from
  the project's files or decide with its own judgement.
- Write each instruction as briefly as the agent can still follow it.
- Put in `SKILL.md` only what every use of the skill needs. Put what only some uses need
  in a reference file, and have `SKILL.md` tell the agent to read it for those uses.
- Use an example only to steer the output's format, tone or structure. Anywhere else,
  leave it out: an example constrains the agent to a certain exploration space.
- Use plain words that a developer new to the project understands on the first read.
- Use one word for each idea throughout the skill.
- Give a reason only where it helps the agent apply an instruction to a case the
  instruction doesn't name, and only a reason that is true.
- When you add or change an instruction in a skill that has a section in
  [docs/skill-sources.md](../../../docs/skill-sources.md), update its entry there.
