# Where the skills' instructions come from

The [writing-skills](../.claude/skills/writing-skills/SKILL.md) and
[authoring-writing-rules](../.claude/skills/authoring-writing-rules/SKILL.md) skills
state their guidance as instructions, without reasons an agent doesn't need. This page
records where each instruction comes from, for anyone who wants to check or change one.
When an instruction in one of those skills changes, its entry here changes with it.

The sources are:

- [The new rules of context engineering for Claude 5 generation models](https://claude.dev/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models/)
  (Jul 24, 2026), here "the Claude 5 post".
- [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices).
- [Extend Claude with skills](https://code.claude.com/docs/en/skills), here "the skills
  page".
- [Test plugins with evals](https://code.claude.com/docs/en/plugin-evals.md), here
  "plugin evals".

An instruction not listed here is codeguard's own decision.

## writing-skills

- **Write the `description` so the skill loads when it's needed.** The skills page: the
  `description` "helps Claude decide when to load the skill automatically".
- **Write only what the agent wouldn't know or do unaided.** The Claude 5 post, on
  skills: "It's best when skills encode particular opinions, knowledge, or best practices
  that are particular to you, your team, or product", and "Avoid making them
  overconstrained, except in highly important areas".
- **Write each instruction as briefly as the agent can still follow it.** The Claude 5
  post: "We removed over 80% of Claude Code's system prompt … with no measurable loss on
  our coding evaluations". The skills page: "Keep the body itself concise. Once a skill
  loads, its content stays in context across turns, so every line is a recurring token
  cost".
- **Put in `SKILL.md` only what every use needs.** The Claude 5 post: "For long skills,
  try and use progressive disclosure as much as possible". The skills page: it "keeps
  `SKILL.md` focused on the essentials while letting Claude access detailed reference
  material only when needed".
- **Use an example only to steer format, tone or structure.** Prompting best practices:
  "Examples are one of the most reliable ways to steer Claude's output format, tone, and
  structure". The Claude 5 post, in its section on tool usage: "giving examples actually
  constrains them to a certain exploration space".
- **Use plain words.** Prompting best practices: "Show your prompt to a colleague with
  minimal context on the task … If they'd be confused, Claude will be too".
- **Give a reason only where it helps the agent generalize.** Prompting best practices:
  "Claude can generalize from the explanation". The skills page: "State what to do rather
  than narrating how or why".

## authoring-writing-rules

### Writing the skill

- **Agree with codeguard's architecture and Rule formats.** codeguard's decision: those
  docs define what a rule is.
- **Write the `description` so the skill loads when someone asks for a rule.** Plugin
  evals: "Claude isn't choosing your skill on natural phrasing. Adjust the skill's
  `description`".
- **Keep everything the agent reads inside the skill.** codeguard's decision: the agent
  works in another project, without codeguard's docs.
- **Give no lists of words to match.** codeguard's decision: a list decides only the
  words it names.
- **Say what a rule must be, in codeguard's public terms.** codeguard's decision: how the
  judge reads a rule is codeguard's internals.

### Writing its evals

- **Test only the skill.** codeguard's decision: a rule the agent writes is tested
  wherever that rule lives.
- **Write the prompt as a person would ask.** Plugin evals: "The prompt is something a
  person using your plugin might type".
- **Give every case result graders and a `tool_used: Skill` grader.** Plugin evals: "Give
  each case one grader on the result, such as the final message or a produced file, and
  one on the steps Claude took to produce it, such as `tool_used` or `tool_order`.
  Together they tell you both whether the answer was right and whether your plugin
  produced it".
- **Check structure with a `regex` grader.** Plugin evals: "For long output such as a
  generated file, grade it with a `regex` grader over the file's contents, which checks
  the whole file the same way every time". Keeping each pattern short enough to verify
  at a glance is codeguard's decision.
- **Give an `llm` grader short text to read.** Plugin evals: "An `llm` grader asks a
  model for a verdict, so its answer can differ between runs, and it differs more the
  longer the text it has to read", and "Keep `llm` graders for short outputs".
- **Write the rubric as concrete `PASS if` and `FAIL if` conditions.** Plugin evals:
  "rubrics written as concrete PASS and FAIL conditions".
- **Leave the output's formatting out of the verdict.** Plugin evals: "A small judge
  model can mark a correct answer wrong because it's formatted differently from what the
  rubric describes".
