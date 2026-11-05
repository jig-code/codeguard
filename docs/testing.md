# How to test your changes

This guide tells you how to test a change before you merge it, whether you are working
on codeguard itself, on a rule package such as
[betterwithranch/codeguard-rules](https://github.com/betterwithranch/codeguard-rules), or
on an app that uses codeguard. Find the section for the repository you are changing,
then the row for the kind of change you made. Each row says what CI checks and which
commands run the same checks on your machine, so you can find a failure before CI does.
The rows list every check a change needs: a change needs no check its row doesn't name.

## Words

A codeguard rule is one of two kinds. Its files sit in a rule directory: `.codeguard/` in
an app, or each ruleset's directory in a rule package. The paths below are relative to
that directory, and the layout is fixed.

- A pattern rule is an ast-grep rule that matches code exactly, in
  `rules/pattern/<id>.yml`. Its rule tests, `rule-tests/<id>-test.yml`, list code it
  must and must not match.
- A judge rule is a requirement a model checks. Its skill, `skills/<id>/SKILL.md`, is the
  requirement's text, which codeguard puts in the judge's prompt; it isn't a Claude Code
  skill. A supplement beside it gives one language's forms of the requirement.
  Its rule eval, `rule-evals/<id>.yaml`, lists cases: each is an edit and the review it
  should get.
- A rule's binding, `bindings/<id>.yaml`, sets the paths it reviews. A judge rule's
  binding also sets its triggers: the code a change must touch for the judge to check
  it. A trigger is a built-in change kind or a gate, an ast-grep rule in
  `gates/<id>.yml`, tested like a pattern rule.
- The judge is the code in codeguard that sends a judge rule and a change to the model
  and turns its reply into a review.

`valid`, `invalid` and `skipped` are what a rule eval case expects. `invalid`: the
triggers fire and the judge reports a violation. `valid`: the triggers fire and the
judge reports none. `skipped`: the triggers don't fire.

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

CI runs a rule's eval only for a change that can change its verdicts:

| You change | Each case of the rule passes |
|---|---|
| The rule: its skill or a language supplement, its binding (paths, triggers), or a gate its triggers name. Or the rule's eval cases | 20 runs of 20 |
| The judge: codeguard's judge prompt, request, tools or harness, or the codeguard version a package or app tests with | 3 runs of 3 |

Twenty clean runs show, with 95% confidence, that a case fails less than 1 run in 7.
Three clean runs catch a rule that a judge change has broken. No other change runs a
rule eval: a pattern rule, a gate no judge rule uses, or another rule. CI applies this
wherever rules that review code live: a rule package and an app's `.codeguard/`.
codeguard's fixture rules only exercise the judge, so a change to one is tested like a
judge change.

Re-running until a case passes doesn't meet the bar.

For case construction, follow the writing-rules reference's
[eval case guidance](../skills/writing-rules/references/judge-rules.md#write-a-few-clear-eval-cases).
It applies to rule evals in packages and apps and to CodeGuard's pytest judge fixtures,
including cases that deliberately contain pre-existing violations to test review scope.

Rule test warnings, such as broad triggers, are advisory: they don't fail a change.

## Changing codeguard

| You change | It checks | CI runs | Locally, run |
|---|---|---|---|
| Anything | Lint, format, import boundaries, types and codeguard's offline tests | `uv run ruff check`, `uv run ruff format --check`, `uv run lint-imports`, `uv run basedpyright`, `uv run pytest` | Same |
| Anything | The changed files against the rules this repository opts into in its [`.codeguard/config.yaml`](../.codeguard/config.yaml), judge rules included; an error fails. This dogfoods codeguard: every change to it must pass the rules in its own config. In CI, the review action reviews the pull request's changes since its base branch. Locally, `codeguard review` reviews uncommitted and untracked files | `codeguard review --base <base branch>` | `codeguard review` |
| The judge: its review, provider, rules or syntax code, or the dependencies. Or a fixture rule or its fixture cases | Each fixture case's review, 3 runs | `uv run pytest -m llm -n 4` | Same |
| The writing-rules skill or its evals | Each skill eval case's graders: 1 run to verify the change, then 9 more, every grader passing every run | `claude plugin eval .` with the flags in [Testing the writing-rules skill](skill-evals.md) | Same |

The judge's code is under `src/codeguard/`. Plain `uv run pytest` deselects the LLM
tests. `-n 8` only sets how many run at once: any number gives the same result.

codeguard ships no rules, so `codeguard rules test` and `codeguard rules eval` don't
run here. The rules in `evals/judge/` are fixtures for codeguard's own tests, and the
rules codeguard reviews itself with are tested in their package's CI.

## Changing a rule package

| You change | It checks | CI runs | Locally, run |
|---|---|---|---|
| A pattern rule, a gate or their tests | Each rule and gate matches its `invalid` snippets and none of its `valid` ones | `codeguard rules test` | Same |
| A judge rule's skill, supplement, binding or rule eval, or a gate it uses | Each case's triggers, then each such rule's verdicts, 20 runs | `codeguard rules test`, `codeguard rules eval --rule <id> --repeat 20` | Same |
| The codeguard version CI tests with | Each case's triggers, then every judge rule's verdicts, 3 runs | `codeguard rules test`, `codeguard rules eval --repeat 3` | Same |

Run both commands at the package root; they cover every ruleset.

## Changing an app

| You change | It checks | CI runs | Locally, run |
|---|---|---|---|
| The app's code | The changed files against the app's rules; an error fails. In CI, the review action reviews the pull request's changes since its base branch. Locally, `codeguard review` reviews uncommitted and untracked files | `codeguard review --base <base branch>` | `codeguard review` |
| A rule the app defines | Each rule's tests and each case's triggers, then the verdicts of each judge rule whose rule or eval cases changed, 20 runs | `codeguard rules test`, `codeguard rules eval --rule <id> --repeat 20` | Same |
| The codeguard release the actions are pinned to | Each case's triggers, then every judge rule's verdicts, 3 runs | `codeguard rules test`, `codeguard rules eval --repeat 3` | Same |

- An app with no rules of its own has only the first row.
- A packaged rule is tested in its package's CI, not the app's.
