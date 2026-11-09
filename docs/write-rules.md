# Write rules

For whoever writes a project's own rules or maintains a rule package. The plugin's
[writing-rules skill](../skills/writing-rules/SKILL.md) says which kind of rule fits a
convention and how to state it; [Rule formats](rule-formats.md) has the
format of each file.

## Where rules live

A project's own rules live in `.codeguard/`. A rule package is a git repo with a
`codeguard-package.yaml` at its root:

```yaml
name: codeguard
rulesets: [python]
ast-grep: ">=0.45"         # the ast-grep versions its pattern rules work with
codeguard: ">=0.2"         # the codeguard versions that can load it
```

This file lives in the package. A project's config never names the package: it picks it
by git URL and ref, and its rulesets and rules by their own names
([Opt into a rule package](add-codeguard.md#opt-into-a-rule-package)). The `name` shows
only in diagnostics, as in `codeguard/python/no-del-param`.

Each ruleset is a directory with the same layout as a project's `.codeguard/`:

```
python/
  rules/pattern/<id>.yml     # ast-grep rules
  gates/<id>.yml             # ast-grep rules that gate judge rules
  rule-tests/<id>-test.yml   # tests for both, with __snapshots__/
  skills/<id>/SKILL.md       # judge rules
  bindings/<id>.yaml         # a rule's paths; a judge rule's triggers and model
  rule-evals/<id>.yaml       # rule evals: test cases for judge rules
```

A binding or rule eval may end in `.yaml` or `.yml`. Pattern rule tests in
`rule-tests/pattern/`, the old layout, still run. codeguard rejects anything else in a
ruleset directory, and in `.codeguard/` anything else but `config.yaml`, so a rule
moves between a project and a package unchanged.

## Why a rule exists

Every rule says why it exists; the `writing-rules` skill says what to write and where.
`codeguard test` reports each rule without a why ([`--missing-why`](cli.md#test)).

## Judge rules

A judge rule is three files, all named by its id:

```
python/
  skills/<id>/SKILL.md       # the rule the judge checks
  bindings/<id>.yaml         # where it runs, when it runs, and the model that judges it
  rule-evals/<id>.yaml       # the rule eval: edits and the review each should get
```

The rule eval is what makes a rule trustworthy. It shows the rule flags the edits it
should and passes the ones it should, on the model that will judge it in reviews: the
binding's ([Choose a judge](judges.md)). To move a rule to another model, change its
binding and pass its rule eval again.

`codeguard eval` judges with the binding's model too, unless `--provider` names another.
That is for a package whose bar is passing on more than one model, such as a CI job per
provider; it changes nothing a review judges with.

## Test a judge rule

1. `codeguard test` checks the triggers on every case, with no model call.
2. `codeguard eval` reviews every case once with the binding's model, the way
   `codeguard review` would, to verify the change.
3. Once it passes, `codeguard eval --repeat 2` reviews each case twice more, so an
   unstable verdict shows up as a failing run, named like
   `a second class added to the file [2/2]`. A case passes when it gets its expected
   review on all 3 runs.

`codeguard eval -h` lists its options for judging part of a package, or with another
model ([CLI](cli.md#eval)). [What makes a case fail](rule-formats.md#what-makes-a-case-fail)
lists each command's failures.

An eval tests the rule, not the code, so every run calls the model. With a Logfire token
each rule's run is also in Logfire, as an experiment named `<rule> on <model>`, so runs
of the same rule compare ([Telemetry](telemetry.md)).

A project tests the rules in its `.codeguard/` the same way a package does.
[Testing](testing.md#changing-a-rule-package) says which test each change needs.

## Package CI and releases

Run `codeguard test` and `codeguard eval` at the package root; they cover every ruleset.
Tag releases `v<major>.<minor>.<patch>`; projects name the tag as their `ref`.
[jig-code/codeguard-rules](https://github.com/jig-code/codeguard-rules) is
an example.

## Try a local package

`kind: path` with `path: ../my-rules` in place of `git` uses a local package, for
working on one. To use it without editing the committed config, put that config in a
gitignored file such as `codeguard.local.yaml` and set
`CODEGUARD_CONFIG=codeguard.local.yaml`. The path is relative to the repository root.

## A private package

For a private package in CI, pass the action a token that can read it:

```yaml
      - uses: jig-code/codeguard@v0.11.0
        with:
          claude-code-oauth-token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
          packages-token: ${{ secrets.CODEGUARD_PACKAGES_TOKEN }}
```
