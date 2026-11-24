# Testing codeguard

This guide says which of codeguard's tests a change needs you to run.

Hooks in [`.claude/settings.json`](../.claude/settings.json) run the other checks: each
Python file an agent edits is formatted, and when an agent stops, ruff, `lint-imports`,
basedpyright and codeguard's review run, and an error blocks the stop. CI runs them on
pull requests too.

## Which tests to run

| You change | Run |
|---|---|
| Any file outside `docs/`, `.claude/skills/`, `README.md` and `CLAUDE.md` | `uv run pytest` |
| The judge: its review, provider, rules or syntax code, or the dependencies. Or a fixture rule or its fixture cases | The LLM tests: `uv run pytest -m llm -n 4 --llm-runs 1 -x`, then `uv run pytest -m llm -n 4 --llm-runs 2` |
| The writing-rules skill or its evals | The skill evals ([The skill evals](#the-skill-evals)), with `--runs 1`, then with `--runs 2` |
| A project skill in `.claude/skills/` | A few prompts a person would type for the skill's task, each in a fresh session: the skill loads, and the output follows it |

A change to only `docs/`, `README.md` or `CLAUDE.md` needs no test. CI runs these tests
on pull requests; run them first, so a failure shows before CI spends a run on it.

The judge is the code in `src/codeguard/` that sends a judge rule and a change to the
model and turns its reply into a review. Its fixtures, in `evals/judge/`, are a small
rule package that exists only to test it. A fixture rule is a judge rule there, and a
fixture case is one of its rule eval cases.

Three kinds of eval call a model, and each tests something different:

- The LLM tests test the judge: that it reaches the right verdict on a rule and a
  change. Their cases are the fixture cases.
- The skill evals test the writing-rules skill: that an agent following it writes good
  rules ([The skill evals](#the-skill-evals)).
- Rule evals, run with `codeguard eval`, test a project's or package's judge rules: that
  each rule's wording gets the right verdicts. They are a codeguard feature, not one of
  codeguard's tests ([The rule eval](rule-formats.md#the-rule-eval)).

Plain `uv run pytest` calls no model and deselects the LLM tests. `-n 4` only sets how
many LLM tests run at once: any number gives the same result.

The LLM tests call Gemini, so they need Gemini's credentials
([Gemini on Google Cloud](judges.md#gemini-on-google-cloud)). In an environment whose
proxy injects the Vertex AI credentials, run them as
`CODEGUARD_JUDGE__GEMINI__PROJECT=<project> CODEGUARD_JUDGE__GEMINI__API_KEY=proxy-injected <command>`,
where `<project>` is your Google Cloud project.

## Tests that call a model

A review judges each change once, so a case that flips between runs is a review that
wrongly blocks or misses. The LLM tests and the skill evals call a model, so each runs
in two passes. The first command runs each case once to verify the change, and the LLM
tests stop at the first failure, so a broken change costs one run. Once it passes with
nothing changed since, the second command runs each case twice more. A case passes only
when it passes all 3 runs. Any change starts again at the first command.

Re-running until a case passes doesn't meet the bar.

## The skill evals

The skill evals run the writing-rules skill's cases, in `plugin/evals/writing-rules/`:

```sh
claude plugin eval ./plugin --scaffold --allow-tools Write Edit \
  --runs 1 --threshold 1 --ablation none \
  --model <agent model> --judge-model claude-haiku-5-5 \
  --trust-plugin --no-publish
```

Then run it again with `--runs 2`. The graders run on Haiku 5.5, for speed and cost.
`--case <name>` runs only the case a change touches. The command runs on a signed-in
`claude` CLI. On Bedrock, set `CLAUDE_CODE_USE_BEDROCK=1` and give both models as Bedrock
model ids or inference profiles; CI takes them from the `SKILL_EVALS_AGENT_BEDROCK_MODEL`
and `SKILL_EVALS_GRADER_BEDROCK_MODEL` repository variables
([`skill-evals.yaml`](../.github/workflows/skill-evals.yaml)).

When a change adds a case, adds or removes a grader, or changes what the skill tells the
agent to do, also run the command once with `--ablation with-without --runs 2`. In the
runs without the skill, the whole plugin is left out. A case that passes in both arms
doesn't need the skill: read what the agent wrote without it to see why.

[Writing the skill's evals](../.claude/skills/authoring-writing-rules/references/evals.md)
says how to write a case and its graders.
