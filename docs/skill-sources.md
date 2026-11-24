# Where the skills' guidance comes from

The [writing-skills](../.claude/skills/writing-skills/SKILL.md) and
[authoring-writing-rules](../.claude/skills/authoring-writing-rules/SKILL.md) skills draw
on these sources. Guidance none of them covers is codeguard's own decision.

- [The new rules of context engineering for Claude 5 generation models](https://claude.dev/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models/)
  (Jul 24, 2026): writing only what the agent wouldn't know, brevity, progressive
  disclosure, and when examples constrain.
- [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices):
  plain words, when to give a reason, and examples that steer format.
- [Extend Claude with skills](https://code.claude.com/docs/en/skills): the `description`,
  a concise body, and what goes in `SKILL.md` versus a reference file.
- [Test plugins with evals](https://code.claude.com/docs/en/plugin-evals.md): eval
  prompts, result graders and the `tool_used` grader, `regex` versus `llm` graders, and
  rubrics.
