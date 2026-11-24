# Testing the writing-rules skill

The skill's evals are in
[`plugin/evals/writing-rules/`](../../../../plugin/evals/writing-rules/) and run with
`claude plugin eval`. [Test plugins with evals](https://code.claude.com/docs/en/plugin-evals.md)
explains the command, how to write a case and its graders, and how cases are scored. This
page says only what codeguard adds. [Testing codeguard](../../../../docs/testing.md) says
when to run them.

## What the evals check

Each case asks an agent with the skill for a codeguard rule, and grades what the agent
does against what the skill tells it to do.

The evals test only the skill, and the skill itself covers only writing the rule. They
never check whether a rule the agent writes works, what verdict codeguard would give on
any code, or whether its rule tests or rule evals pass: that is tested wherever the rule
lives. When the agent declines a rule, they don't check what it says about the other tool
or whether it sets that tool up. So:

- A case never runs codeguard. The agent gets `Write` and `Edit`, never `Bash`.
- Each case has an obvious right answer: two reviewers who read what the agent wrote give
  it the same verdict.
- A case's prompt is something a person might type to ask for a rule, a new one or a fix
  to an existing one, and it names the files the agent needs
  ([Test plugins with evals](https://code.claude.com/docs/en/plugin-evals.md)).
- A grader reads one thing: a file that the agent wrote, whether the agent wrote any
  rule file, whether the agent loaded the writing-rules skill, or, in a case that
  declines a rule, the agent's final reply.
- A case's graders check its result and its steps: "Together they tell you both whether
  the answer was right and whether your plugin produced it"
  ([Test plugins with evals](https://code.claude.com/docs/en/plugin-evals.md)). The result
  graders check only the instruction the case targets: as many as that instruction needs,
  one check each.
- An instruction that applies to every rule gets a case of its own, not a grader in every
  case.
- An `llm` grader's rubric is "written as concrete PASS and FAIL conditions"
  ([Test plugins with evals](https://code.claude.com/docs/en/plugin-evals.md)), and holds
  everything the judge needs to decide.
- Every case has a `tool_used: Skill` grader that passes when the agent loads the
  writing-rules skill, written as in
  [Write a case manually](https://code.claude.com/docs/en/plugin-evals.md#write-a-case-manually).

Cases are named like unit tests, so the names alone say what each case tests:

- A case's directory is its expected outcome, then what only that case tests.
- Every case with the same outcome starts with the same outcome name, so each outcome has
  one name.
- A grader's file is its number, then what the agent's output does.

[Choose graders that give a stable signal](https://code.claude.com/docs/en/plugin-evals.md#choose-graders-that-give-a-stable-signal)
says when to use each grader type. A `regex` pattern is short enough to check at a
glance, and checks structure. What prose says is judged by an `llm` grader, because a
pattern breaks on wording that does what the skill asks.

"An `llm` grader asks a model for a verdict, so its answer can differ between runs, and it
differs more the longer the text it has to read"
([Test plugins with evals](https://code.claude.com/docs/en/plugin-evals.md)). An `llm`
grader judges one criterion. Its `FAIL if` sentences name that criterion's concrete
failures, a missing or empty output among them. An `llm` grader has no examples, and no
lists of words to match, for the reasons
[What the skill must be](../SKILL.md#what-the-skill-must-be) gives.
[Write a case manually](https://code.claude.com/docs/en/plugin-evals.md#write-a-case-manually)
gives the rubric's form.

## Running them

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

Before a new or changed `llm` grader counts, read its verdicts and the output it judged on
a few runs: "A small judge model can mark a correct answer wrong because it's formatted
differently from what the rubric describes"
([Test plugins with evals](https://code.claude.com/docs/en/plugin-evals.md)).

When a change adds a case, adds or removes a grader, or changes what the skill tells the
agent to do, also run the command once with `--ablation with-without --runs 2`. The runs
without it leave out the whole plugin:

- "If a case scores 1.0 both with and without the plugin, the plugin isn't what made it
  pass" ([Test plugins with evals](https://code.claude.com/docs/en/plugin-evals.md)). Read
  what the agent wrote in those runs to see why.
- A grader's verdicts in the runs without the plugin are never tuned.
- The `tool_used: Skill` grader is left out of those runs: "A check like "the skill was
  invoked" can never pass without the plugin" (the same page).

CI runs them from `.github/workflows/skill-evals.yaml`.
