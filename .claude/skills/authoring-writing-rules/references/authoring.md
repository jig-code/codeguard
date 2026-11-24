# Authoring the writing-rules skill

## Goal

Someone asks for a convention to be enforced. An agent with the skill either writes a
codeguard rule that gives the right verdict on any code the convention covers, or
declines when another tool should check it. A rule "states one requirement on code and
why it matters" ([codeguard's architecture](../../../../docs/architecture.md#rules)).

## What the skill must be

- **Agrees with codeguard's docs.** What a rule is, its two kinds, its files and its why
  are defined in [codeguard's architecture](../../../../docs/architecture.md#rules) and
  [Rule formats](../../../../docs/rule-formats.md). The skill never contradicts them, and adds only what
  an agent needs beyond them.
- **Loads when a rule is asked for.** An agent picks the skill by its `description`;
  when the skill doesn't load, "Claude isn't choosing your skill on natural phrasing.
  Adjust the skill's `description`" ([Test plugins with evals](https://code.claude.com/docs/en/plugin-evals.md)).
- **Only what the agent wouldn't know or do unaided.** Let the model "use surrounding
  context and judgement instead", and avoid "stating 'the obvious' things Claude should
  know by looking at your file system or your repo" ([The new rules of context
  engineering for Claude 5 generation models](https://claude.dev/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models/)).
- **Everything the agent reads ships with the skill.** The agent works in another
  project, with the codeguard CLI and this skill, and none of codeguard's docs.
- **Brief.** "We removed over 80% of Claude Code's system prompt … with no measurable
  loss on our coding evaluations", and "The same can be applied to your own CLAUDE.md
  and Skill.md files" ([The new rules of context engineering for Claude 5 generation
  models](https://claude.dev/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models/)).
- **Few rules, loaded when needed.** "Avoid making them overconstrained, except in highly
  important areas", and "For long skills, try and use progressive disclosure as much as
  possible" (the same post). `SKILL.md` holds only what every request needs. What only
  some requests need, such as one kind of rule, goes in a reference file that `SKILL.md`
  has the agent read only for those requests.
- **No examples.** "giving examples actually constrains them to a certain exploration
  space" (the same post).
- **No lists of words to match.** A list of words decides only the words it names.
- **Plain words.** A developer new to the project understands each instruction on the
  first read.
- **One word for each idea.** Code *keeps* or *breaks* a rule, everywhere in the skill.
- **Describes rules, not the judge.** The skill uses codeguard's public terms, such as
  *judge rule*, and says what a rule must be. How the judge reads a rule is codeguard's
  internals.
- **Says what to do.** Each instruction in the skill says what the agent should produce:
  "Being specific about the output you want can help enhance results" ([Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)).
- **A reason where it helps the agent generalize.** "Claude can generalize from the
  explanation" (the same page). A reason that isn't true is left out.
