# Testing codeguard

This guide says which of codeguard's tests a change needs you to run.

Hooks in [`.claude/settings.json`](../.claude/settings.json) run the other checks: each
Python file an agent edits is formatted, and when an agent stops, ruff, `lint-imports`,
basedpyright and codeguard's review run, and an error blocks the stop. CI runs them on
pull requests too.

## Which tests to run

| You change | Run |
|---|---|
| Any file outside `docs/`, `README.md` and `CLAUDE.md` | `uv run pytest` |
| The judge: its review, provider, rules or syntax code, or the dependencies. Or a fixture rule or its fixture cases | The LLM tests: `uv run pytest -m llm -n 4 --llm-runs 1 -x`, then `uv run pytest -m llm -n 4 --llm-runs 2` |
| The writing-rules skill or its evals | The skill evals: `claude plugin eval ./plugin` with the flags in [Testing the writing-rules skill](skill-evals.md), run with `--runs 1`, then with `--runs 2` |

A change to only `docs/`, `README.md` or `CLAUDE.md` needs no test. CI runs these tests
on pull requests; run them first, so a failure shows before CI spends a run on it.

The judge is the code in `src/codeguard/` that sends a judge rule and a change to the
model and turns its reply into a review. Its fixtures, in `evals/judge/`, are a small
rule package that exists only to test it. A fixture rule is a judge rule there, and a
fixture case is one of its rule eval cases.

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

For a fixture case, follow the writing-rules reference's
[eval case guidance](../plugin/skills/writing-rules/references/judge-rules.md#write-a-few-clear-eval-cases).
A fixture that tests review scope may also hold a pre-existing violation of the rule under
test, in code the change leaves untouched and doesn't take part in, so the review must
leave it unreported. Keep that violation small and plain, and let it break no other
rule, so nothing else in the fixture obscures the behavior under test.
