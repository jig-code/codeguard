# The writing-rules skill

The writing-rules skill, in `plugin/skills/writing-rules/`, is the guidance codeguard's
plugin gives an agent that writes or changes a codeguard rule. The
authoring-writing-rules skill holds the guidance for changing it, for people and agents
alike:

- [Its `SKILL.md`](../.claude/skills/authoring-writing-rules/SKILL.md) says what the
  writing-rules skill must achieve and what it must be. Every instruction in the
  writing-rules skill traces to an item in it; an instruction that traces to none is
  removed.
- [Testing the writing-rules skill](../.claude/skills/authoring-writing-rules/references/testing.md)
  says how its evals check that, and how to run them.
