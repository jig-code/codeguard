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
| A rule codeguard should check: a new one, or a fix to an existing one | Write or fix the rule as the skill says | The rule's files: `.codeguard/skills/<id>/SKILL.md`, `.codeguard/bindings/<id>.yaml` and `.codeguard/rule-evals/<id>.yaml` | `created-flag-tuples` asks for a rule that functions don't return a `(thing, created)` pair; a grader checks that the rule eval gives the framework's `get_or_create` call a `valid` case |
| A rule another tool should check, such as a type checker or a dead-code tool | Write no rule, and say why | That no rule file was written, and that the agent's reply says the convention isn't a codeguard rule's to check | `declines-a-dead-code-rule` asks for a judge rule that flags a function nobody calls, which takes a lookup across the whole repository |

The evals test only the skill. They never check whether a rule the agent writes works,
or whether its rule tests or rule evals pass: that is tested wherever the rule lives.
When the agent declines a rule, they don't check what it says about the other tool or
whether it sets that tool up. So:

- A case never runs codeguard. The agent gets `Write` and `Edit`, never `Bash`.
- A grader reads one file the agent wrote, checks that it wrote no rule file, or, in a
  case that declines a rule, reads the agent's final reply.

## Running them

CI runs them when `skills/writing-rules/`, `evals/writing-rules/` or their workflow
changes, through Bedrock, in two passes. The validity pass runs every case once to
verify the change. Once it passes with nothing changed since, the reliability pass runs
every case 9 more times, to the end, and reports each case's score. A case passes when
every grader passes in all 10 runs. Any change starts again at the validity pass.

The agent runs on Claude Opus 5.5 (`us.anthropic.claude-opus-5-5`) and the graders on
Claude Haiku 5.5 (`us.anthropic.claude-haiku-5-5`), each by its Bedrock cross-region
inference profile. The repository variables `SKILL_EVALS_AGENT_BEDROCK_MODEL` and
`SKILL_EVALS_GRADER_BEDROCK_MODEL` are optional: each, when set, overrides its own
default, for example with an application inference profile ARN. `CLAUDE_AWS_ROLE`, the
AWS role CI assumes, is required.

```sh
export CLAUDE_CODE_USE_BEDROCK=1
claude plugin eval . --scaffold --allow-tools Write Edit --runs 1 --threshold 1 \
  --model "$SKILL_EVALS_AGENT_BEDROCK_MODEL" \
  --judge-model "$SKILL_EVALS_GRADER_BEDROCK_MODEL" \
  --trust-plugin --no-publish
claude plugin eval . --scaffold --allow-tools Write Edit --runs 9 --threshold 1 \
  --model "$SKILL_EVALS_AGENT_BEDROCK_MODEL" \
  --judge-model "$SKILL_EVALS_GRADER_BEDROCK_MODEL" \
  --trust-plugin --no-publish
```

CI runs the two as separate jobs, the second starting when the first passes.
`claude plugin eval` has no option to stop at the first failing case, so the validity
pass runs every case once before it fails.

For diagnosis, each CI job also passes `--keep-temp` and `--json`, and uploads a
`skill-evals-validity-results` or `skill-evals-reliability-results` artifact. It holds
`aggregate-result.json`, `report.html`, `full-result.json` with each grader's
explanation, and each run's `trace.jsonl`. The graders still read only the files the
agent wrote; the traces are only for finding out why a case failed.

Run it from a checkout with no `.venv`: the eval copies the plugin and refuses the hard
links uv makes there.
