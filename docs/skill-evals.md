# Testing the writing-rules skill

The writing-rules skill, in `skills/writing-rules/`, is the guidance codeguard's plugin
gives an agent that writes or changes a codeguard rule. Its evals are in
`evals/writing-rules/` and run with `claude plugin eval`.
[Test plugins with evals](https://code.claude.com/docs/en/plugin-evals.md) explains the
command, how to write a case and its graders, and how cases are scored. This page says
only what codeguard adds. [How to test your changes](testing.md) covers testing
codeguard, testing rules and reviewing code.

## What the evals check

Each case asks an agent with the skill for a codeguard rule, and grades what the agent
does against what the skill says. A case is one of two kinds:

| The agent is asked for | It should | Graders check | Example |
|---|---|---|---|
| A rule codeguard should check: a new one, or a fix to an existing one | Write or fix the rule as the skill says | The rule's files: `.codeguard/skills/<id>/SKILL.md`, `.codeguard/bindings/<id>.yaml` and `.codeguard/rule-evals/<id>.yaml` | Asked for a rule that a function named as a query changes no state, the agent writes the rule's three files; a grader reads the rule eval for a `valid` case of a getter that only reads beside an `invalid` getter that saves |
| A rule another tool should check, such as a type checker or a dead-code tool | Write no rule, and say why | That no rule file was written, and that the agent's reply says the convention isn't a codeguard rule's to check | Asked for a rule that every call passes the arguments its function requires, the agent writes no files and replies that the type checker decides it |

The evals test only the skill. They never check whether a rule the agent writes works,
or whether its rule tests or rule evals pass: that is tested wherever the rule lives.
When the agent declines a rule, they don't check what it says about the other tool or
whether it sets that tool up. So:

- A case never runs codeguard. The agent gets `Write` and `Edit`, never `Bash`.
- A grader reads one file the agent wrote, checks that it wrote no rule file, or, in a
  case that declines a rule, reads the agent's final reply.
- Each case also has a `tool_used` grader that checks the agent invoked the skill. It
  shows whether the skill fired and doesn't count toward the score.

## Writing a case

A case measures whether the skill's instructions lead an agent to the right result, so
a failure means the skill didn't get the agent there:

- Each grader checks one instruction the skill states, in the skill's terms. A grader
  never asks for more than the skill says: a quality the skill doesn't require goes into
  the skill first.
- A grader checks the instruction, never an example the skill gives for it, and the
  skill's examples never contain a case's answer. A case the skill's example answers
  measures whether the agent copied it.
- The skill's instructions decide the case's prompt: the right result follows from the
  skill alone, with no outside knowledge and no judgment call either way.
- A grader the agent passes as often without the skill as with it measures nothing the
  skill adds: drop it. `claude plugin eval` runs each case with and without the plugin,
  and reports the difference as `Δ`.
- When a grader fails or flips, find which side is wrong. If the agent missed an
  instruction, make the instruction clearer or put it where the agent reads it. If the
  grader asks for more than the skill says, fix the grader. Neither is reworded only to
  pass.

## Running them

CI runs them when `skills/writing-rules/` or `evals/writing-rules/` changes. Each case
runs 3 times, and passes when at least 80% of its graders pass, averaged over the runs.

```sh
claude plugin eval . --scaffold --allow-tools Write Edit --runs 3 --threshold 0.8 \
  --trust-plugin --no-publish
```

Run it from a checkout with no `.venv`: the eval copies the plugin and refuses the hard
links uv makes there.
