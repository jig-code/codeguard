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
| A rule codeguard should check: a new one, or a fix to an existing one | Write or fix the rule as the skill says | The rule's files: `.codeguard/skills/<id>/SKILL.md`, `.codeguard/bindings/<id>.yaml` and `.codeguard/rule-evals/<id>.yaml` | `writes-rule-created-flag-tuples` asks for a rule that functions don't return a `(thing, created)` pair; a grader checks that the rule eval gives the framework's `get_or_create` call a `valid` case |
| A rule another tool should check, such as a type checker or a dead-code tool | Write no rule, and say it isn't codeguard's to check, without naming or setting up the other tool | That no rule file was written, and that the agent's reply says the convention isn't a codeguard rule's to check | `declines-unused-functions` asks for a judge rule that flags a function nobody calls any more, which takes a lookup across the whole repository |

The evals test only the skill, and the skill itself covers only writing the rule. They
never check whether a rule the agent writes works, or whether its rule tests or rule
evals pass: that is tested wherever the rule lives. When the agent declines a rule, they
don't check what it says about the other tool or whether it sets that tool up. So:

- A case never runs codeguard. The agent gets `Write` and `Edit`, never `Bash`.
- A grader reads one file the agent wrote, checks that it wrote no rule file, or, in a
  case that declines a rule, reads the agent's final reply.
- A grader checks only what the case's prompt asks for and the skill tells the agent to
  do. A grader on work the prompt doesn't name is a broken case, not a requirement on
  the skill ([Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)).

Cases are named like tests. A case's directory is its expected outcome, then its
subject. The outcome is `writes-rule` (the agent adds a rule), `changes-rule` (it
changes an existing rule) or `declines`. A grader's file is its number, then what
the agent's output does. A grader that checks names is a `regex`, never an `llm` grader.

## Running them

A case passes when every grader passes in all 3 runs. With Bedrock credentials in the
environment, and a Bedrock model id or inference profile for the agent and for the
graders:

```sh
CLAUDE_CODE_USE_BEDROCK=1 claude plugin eval . --scaffold --allow-tools Write Edit \
  --runs 3 --threshold 1 --ablation none \
  --model <agent model id> --judge-model <grader model id> \
  --trust-plugin --no-publish
```

Run it from a checkout with no `.venv`: the eval copies the plugin and refuses the hard
links uv makes there.

CI runs them from `.github/workflows/skill-evals.yaml`.
