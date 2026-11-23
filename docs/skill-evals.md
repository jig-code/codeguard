# Testing the writing-rules skill

The writing-rules skill, in `plugin/skills/writing-rules/`, is the guidance codeguard's
plugin gives an agent that writes or changes a codeguard rule. Its evals are in
`plugin/evals/writing-rules/` and run with `claude plugin eval`.
[Test plugins with evals](https://code.claude.com/docs/en/plugin-evals.md) explains the
command, how to write a case and its graders, and how cases are scored. This page says
only what codeguard adds. [Testing codeguard](testing.md) says when to run them.

## What the evals check

Each case asks an agent with the skill for a codeguard rule, and grades what the agent
does against what the skill says. A case is one of two kinds:

| The agent is asked for | It should | Graders check |
|---|---|---|
| A rule codeguard should check: a new one, or a fix to an existing one | Write or fix the rule as the skill says | The rule's files: `.codeguard/rules/judge/<id>.md`, `.codeguard/bindings/<id>.yaml` and `.codeguard/rule-evals/<id>.yaml` |
| A rule another tool should check, such as a type checker or a dead-code tool | Write no rule, and say that the convention isn't codeguard's to check | That no rule file was written, and that the agent's reply says the convention isn't codeguard's to check |

The cases are in [`plugin/evals/writing-rules/`](../plugin/evals/writing-rules/).

The evals test only the skill, and the skill itself covers only writing the rule. They
never check whether a rule the agent writes works, or whether its rule tests or rule
evals pass: that is tested wherever the rule lives. When the agent declines a rule, they
don't check what it says about the other tool or whether it sets that tool up. So:

- A case never runs codeguard. The agent gets `Write` and `Edit`, never `Bash`.
- A case's prompt asks only for a rule, a new one or a fix to an existing one, and names
  the files the agent needs. It never says why the rule is wanted, who or what reads it,
  or how it behaves when it runs, such as a review it gave or a verdict that changed
  between runs. The skill covers only writing the rule, so none of that is part of a
  case.
- A grader reads one thing: a file that the agent wrote, whether the agent wrote any
  rule file, whether the agent loaded the writing-rules skill, or, in a case that
  declines a rule, the agent's final reply.
- A grader checks only what the case's prompt asks for and the skill tells the agent to
  do. A grader on work the prompt doesn't name is a broken case, not a requirement on
  the skill ([Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)).
  A grader checks the instruction or the ask, never the answer that the fixture's domain
  has, such as which code the rule should flag.
- A grader is changed only when a run of a case misjudged what the agent wrote. Never
  write outputs to test a grader.
- An `llm` grader states the convention and any limit the docs set on what it checks.
  It never refers to the prompt or the docs.
- Every case has a grader that passes when the agent loads the writing-rules skill,
  written as the [skill-fired grader](https://code.claude.com/docs/en/plugin-evals.md#write-a-case-manually).

Cases are named like tests. A case's directory is its expected outcome, then what only
that case tests, never the fixture's topic, so the names alone tell the cases apart. The
outcome is `writes-rule` (the agent adds a rule), `changes-rule` (it changes an existing
rule) or `declines`. A grader's file is its number, then what
the agent's output does.

A fixture file that breaks a rule on purpose is named `<name>.invalid.<ext>`, so a
reviewer can tell it apart from a mistake. The case's `place-files.sh` gives it its real
name when it copies the fixture, so neither the agent nor the graders see the marker.

[Choose graders that give a stable signal](https://code.claude.com/docs/en/plugin-evals.md#choose-graders-that-give-a-stable-signal)
says when to use each grader type. codeguard adds that a `regex` grader's pattern is one
that a reader can check at a glance, and that no grader parses prose with a pattern:
such a pattern is too long for a reviewer to tell what the pattern checks, and the
pattern breaks on wording that does what the skill asks.

An `llm` grader judges one criterion, in plain words: it says what to check the way a
reviewer would say it, with no examples and no lists of words to look for. It states
each check in its own short sentence, with a numbered list where it checks several
things in order. Its `FAIL if` sentences name that criterion's concrete failures. When
several graders read the same output, one of them fails it if it is empty; the others
check only their own criterion. A case passes only when every grader does, and the eval
fails a grader whose file is missing.
[Write a case manually](https://code.claude.com/docs/en/plugin-evals.md#write-a-case-manually) gives the rubric's form.

## Running them

A case passes when every grader passes in all 3 runs: 1 run to verify the change, then,
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

CI runs them from `.github/workflows/skill-evals.yaml`.
