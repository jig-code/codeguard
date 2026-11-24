# The writing-rules skill

The writing-rules skill, in `plugin/skills/writing-rules/`, is the guidance codeguard's
plugin gives an agent that writes or changes a codeguard rule. This page is for authoring
and testing that skill. [Authoring the skill](#authoring-the-skill) says what it must
achieve and what it must be; [Testing the skill](#testing-the-skill) says how its evals
check that. Every instruction in the skill traces to an item under Authoring the skill;
an instruction that traces to none is removed.

## Authoring the skill

### Goal

Someone asks for a convention to be enforced. An agent with the skill either writes a
codeguard rule that gives the right verdict on any code the convention covers, or
declines when another tool should check it. A rule "states one requirement on code and
why it matters" ([codeguard's architecture](architecture.md#rules)).

### What the skill must be

- **Agrees with codeguard's docs.** What a rule is, its two kinds, its files and its why
  are defined in [codeguard's architecture](architecture.md#rules) and
  [Rule formats](rule-formats.md). The skill never contradicts them, and adds only what
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
- **What to do, not what not to do.** Each instruction in the skill tells the agent what
  to do: "Tell Claude what to do instead of what not to do" ([Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)).
- **A reason where it helps the agent generalize.** "Claude can generalize from the
  explanation" (the same page). A reason that isn't true is left out.

## Testing the skill

The skill's evals are in `plugin/evals/writing-rules/` and run with `claude plugin eval`.
[Test plugins with evals](https://code.claude.com/docs/en/plugin-evals.md) explains the
command, how to write a case and its graders, and how cases are scored. This section
says only what codeguard adds. [Testing codeguard](testing.md) says when to run them.

### What the evals check

Each case asks an agent with the skill for a codeguard rule, and grades what the agent
does against what the skill tells it to do. A case is one of two kinds:

| The agent is asked for | It should | Graders check |
|---|---|---|
| A rule codeguard should check: a new one, or a fix to an existing one | Write or fix the rule as the skill says | The rule's files: `.codeguard/rules/judge/<id>.md`, `.codeguard/bindings/<id>.yaml` and `.codeguard/rule-evals/<id>.yaml` |
| A rule another tool should check, such as a type checker or a dead-code tool | Write no rule, say only that the convention isn't codeguard's to check, and offer no other rule | That no rule file was written, that the agent's reply says the convention isn't codeguard's to check, and that the reply offers no other rule |

The cases are in [`plugin/evals/writing-rules/`](../plugin/evals/writing-rules/).

The evals test only the skill, and the skill itself covers only writing the rule. They
never check whether a rule the agent writes works, or whether its rule tests or rule
evals pass: that is tested wherever the rule lives. When the agent declines a rule, they
don't check what it says about the other tool or whether it sets that tool up. So:

- A case never runs codeguard. The agent gets `Write` and `Edit`, never `Bash`.
- A case's prompt is something a person might type to ask for a rule, a new one or a fix
  to an existing one, and it names the files the agent needs
  ([Test plugins with evals](https://code.claude.com/docs/en/plugin-evals.md)).
- A grader reads one thing: a file that the agent wrote, whether the agent wrote any
  rule file, whether the agent loaded the writing-rules skill, or, in a case that
  declines a rule, the agent's final reply.
- Each grader checks that the agent followed one instruction, from the skill or from its
  case's prompt. A grader that checks no instruction is removed.
- An `llm` grader's rubric is "written as concrete PASS and FAIL conditions"
  ([Test plugins with evals](https://code.claude.com/docs/en/plugin-evals.md)), and holds
  everything the judge needs to decide.
- Every case has a grader that passes when the agent loads the writing-rules skill,
  written as the [skill-fired grader](https://code.claude.com/docs/en/plugin-evals.md#write-a-case-manually).

Cases are named like tests. A case's directory is its expected outcome, then its
subject. The outcome is `writes-rule` (the agent adds a rule), `changes-rule` (it
changes an existing rule) or `declines`. A grader's file is its number, then what
the agent's output does.

[Choose graders that give a stable signal](https://code.claude.com/docs/en/plugin-evals.md#choose-graders-that-give-a-stable-signal)
says when to use each grader type. A `regex` pattern is short enough to check at a
glance, and checks structure. What prose says is judged by an `llm` grader, because a
pattern breaks on wording that does what the skill asks.

"An `llm` grader asks a model for a verdict, so its answer can differ between runs, and it
differs more the longer the text it has to read"
([Test plugins with evals](https://code.claude.com/docs/en/plugin-evals.md)). An `llm`
grader judges one criterion. Its `FAIL if` sentences name that criterion's concrete
failures, a missing or empty output among them. An `llm` grader has no examples, and no
lists of words to match, for the reasons [What the skill must be](#what-the-skill-must-be)
gives. [Write a case manually](https://code.claude.com/docs/en/plugin-evals.md#write-a-case-manually) gives the rubric's form.

### Running them

"One run of a non-deterministic agent tells you little, so each case runs three times by
default" ([Test plugins with evals](https://code.claude.com/docs/en/plugin-evals.md)). A
case passes when every grader passes in all 3 runs: 1 run to verify the change, then,
once it passes, 2 more. With Bedrock credentials in the environment, and a Bedrock model
id or inference profile for the agent and for the graders, run the command with
`--runs 1`, then again with `--runs 2`:

```sh
CLAUDE_CODE_USE_BEDROCK=1 claude plugin eval ./plugin --scaffold --allow-tools Write Edit \
  --runs 1 --threshold 1 --ablation none \
  --model <agent model id> --judge-model <grader model id> \
  --trust-plugin --no-publish
```

Without Bedrock, the same command runs on a signed-in `claude` CLI: leave out
`CLAUDE_CODE_USE_BEDROCK=1` and give `--model` and `--judge-model` the names of the
models CI's Bedrock profiles serve. `--case <name>` runs only the case a change touches.

When a change adds a case, adds or removes a grader, or changes what the skill tells the
agent to do, also run the command once with `--ablation with-without --runs 2`:

- Each grader fails without the skill, which shows the skill is needed.
- A grader on the outcome the case requires stays even if it passes without the skill.
- A grader's verdicts in the runs without the skill are never tuned.
- The skill-loaded grader is left out of those runs: "A check like "the skill was
  invoked" can never pass without the plugin"
  ([Test plugins with evals](https://code.claude.com/docs/en/plugin-evals.md)).

CI runs them from `.github/workflows/skill-evals.yaml`.
