# How to test your changes

This guide tells you how to test a change before you merge it, whether you are working
on codeguard itself, on a rule package such as
[jig-code/codeguard-rules](https://github.com/jig-code/codeguard-rules), or
on an app that uses codeguard. Find the section for the repository you are changing,
then the row for the kind of change you made. Each row says what CI checks and which
commands run the same checks on your machine, so you can find a failure before CI does.
The rows list every check a change needs: a change needs no check its row doesn't name.

## Words

A codeguard rule is a pattern rule or a judge rule ([Rules](architecture.md#rules)). Its
files sit in a rule directory: `.codeguard/` in an app, or each ruleset's directory in a
rule package. [Where rules live](write-rules.md#where-rules-live) has the layout, and
[Rule formats](rule-formats.md) the format of each file: bindings, triggers and gates,
and rule eval cases with the `valid`, `invalid` and `skipped` they expect.

The judge is the code in codeguard that sends a judge rule and a change to the model and
turns its reply into a review.

codeguard ships no rules of its own. Its fixtures, in `evals/judge/`, are a small rule
package that exists only to test the judge. A fixture rule is a judge rule there, and a
fixture case is one of its rule eval cases.

Distinguish CodeGuard's repository tests from its rule-validation features:

- `pytest` runs unit and integration tests with model-provider doubles.
- `pytest -m llm` runs tests of the review pipeline with a real judge.
- `codeguard test` and `codeguard eval` are product commands for validating rules.
  Running them manually can provide validation evidence for a change, but does not
  run CodeGuard's repository test suite.

| Test or feature | It checks | Calls a model | A case is |
|---|---|---|---|
| codeguard's tests | The CLI, config, triggers, hooks and judge, with no model | No | A test function |
| LLM tests | The judge gives each fixture case its expected review from a real model | Yes, and verdicts can vary between runs | A fixture case |
| Rule tests | Each pattern rule and gate matches the code it should, and each judge rule's triggers fire on the edits they should | No, and the result is the same every run | Code a rule or gate must or must not match, or a rule eval case, checked for its triggers only |
| Rule evals | Each judge rule's model gives each edit the review it should | Yes, and verdicts can vary between runs | A rule eval case |

Rule tests and rule evals check the rules themselves. `codeguard review` is different: it
runs the rules on your code.

## The bar for a judge rule

A review judges each change once, so a case that flips between runs is a review that
wrongly blocks or misses. A judge rule passes its rule eval when every case gets its
expected review on every run.

A check that calls a model runs in two passes. The validity pass runs each case once to
verify the change, and stops at the first failure, so a broken change costs one run.
Once it passes with nothing changed since, the reliability pass runs each case N-1 more
times, for N in all: 2 more for a rule's 3 runs of 3. The reliability pass never
stops early: it runs every case to the end and reports each case's pass rate, and it
passes only at N of N. Any change starts again at the validity pass. Each row below
gives both passes' commands.

CI runs a rule's eval only for a change that can change its verdicts:

| You change | Each case of the rule passes |
|---|---|
| The rule: its skill directory, its binding (paths, triggers), or a gate its triggers name. Or the rule's eval cases | 3 runs of 3 |
| The judge: codeguard's judge prompt, request, tools or harness, or the codeguard version a package or app tests with | 3 runs of 3 |

Three clean runs catch a rule that a judge change has broken. No other change runs a
rule eval: a pattern rule, a gate no judge rule uses, or another rule. CI applies this
wherever rules that review code live: a rule package and an app's `.codeguard/`.
codeguard's fixture rules only exercise the judge, so a change to one is tested like a
judge change.

Re-running until a case passes doesn't meet the bar.

For case construction, follow the writing-rules reference's
[eval case guidance](../skills/writing-rules/references/judge-rules.md#write-a-few-clear-eval-cases).
It applies to rule evals in packages and apps and to codeguard's pytest judge fixtures.
A fixture that tests review scope may also hold a pre-existing violation of the rule under
test, in code the change leaves untouched and doesn't take part in, so the review must
leave it unreported. Keep that violation small and plain, and let it break no other
rule, so nothing else in the fixture obscures the behavior under test.

Rule test warnings, such as broad triggers, are advisory: they don't fail a change.

## Changing codeguard

| You change | It checks | CI runs | Locally, run |
|---|---|---|---|
| Anything | Lint, format, import boundaries, types and codeguard's offline tests | `uv run ruff check`, `uv run ruff format --check`, `uv run lint-imports`, `uv run basedpyright`, `uv run pytest` | Same |
| Anything | The changed files against the rules this repository opts into in its [`.codeguard/config.yaml`](../.codeguard/config.yaml), judge rules included; an error fails. This dogfoods codeguard: every change to it must pass the rules in its own config. In CI, the review action reviews the pull request's changes since its base branch. Locally, `codeguard review` reviews uncommitted and untracked files | `codeguard review --base <base branch>` | `codeguard review` |
| The judge: its review, provider, rules or syntax code, or the dependencies. Or a fixture rule or its fixture cases | Each fixture case's review: 1 run to verify the change, then 2 more, 3 of 3 | `uv run pytest -m llm -n 4 --llm-runs 1 -x`, then `uv run pytest -m llm -n 4 --llm-runs 2` | Same |
| The writing-rules skill or its evals | Each skill eval case's graders: 1 run to verify the change, then 2 more, every grader passing every run | `claude plugin eval .` with the flags in [Testing the writing-rules skill](skill-evals.md) | Same |

The judge's code is under `src/codeguard/`. Plain `uv run pytest` deselects the LLM
tests. `-n 8` only sets how many run at once: any number gives the same result.

codeguard ships no rules, so `codeguard rules test` and `codeguard rules eval` don't
run here. The rules in `evals/judge/` are fixtures for codeguard's own tests, and the
rules codeguard reviews itself with are tested in their package's CI.

## Changing a rule package

| You change | It checks | CI runs | Locally, run |
|---|---|---|---|
| A pattern rule, a gate or their tests | Each rule and gate matches its `invalid` snippets and none of its `valid` ones | `codeguard rules test` | Same |
| A judge rule's skill directory, binding or rule eval, or a gate it uses | Each case's triggers, then each such rule's verdicts: 1 run to verify the change, then 2 more | `codeguard rules test`, `codeguard rules eval --rule <id>`, then `codeguard rules eval --rule <id> --repeat 2` | Same |
| The codeguard version CI tests with | Each case's triggers, then every judge rule's verdicts: 1 run to verify the change, then 2 more | `codeguard rules test`, `codeguard rules eval`, then `codeguard rules eval --repeat 2` | Same |

Run both commands at the package root; they cover every ruleset.

## Changing an app

| You change | It checks | CI runs | Locally, run |
|---|---|---|---|
| The app's code | The changed files against the app's rules; an error fails. In CI, the review action reviews the pull request's changes since its base branch. Locally, `codeguard review` reviews uncommitted and untracked files | `codeguard review --base <base branch>` | `codeguard review` |
| A rule the app defines | Each rule's tests and each case's triggers, then the verdicts of each judge rule whose rule or eval cases changed: 1 run to verify the change, then 2 more | `codeguard rules test`, `codeguard rules eval --rule <id>`, then `codeguard rules eval --rule <id> --repeat 2` | Same |
| The codeguard release the actions are pinned to | Each case's triggers, then every judge rule's verdicts: 1 run to verify the change, then 2 more | `codeguard rules test`, `codeguard rules eval`, then `codeguard rules eval --repeat 2` | Same |

- An app with no rules of its own has only the first row.
- A packaged rule is tested in its package's CI, not the app's.
