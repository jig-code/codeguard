# Write rules

For whoever writes a project's own rules or maintains a rule package. The plugin's
[writing-rules skill](../skills/writing-rules/SKILL.md) says how to write a rule;
[Rule formats](rule-formats.md) has the format of each file.

## Where rules live

A project's own rules live in `.codeguard/`. A rule package is a git repo with a
`codeguard-package.yaml` at its root:

```yaml
name: betterwithranch
rulesets: [python]
ast-grep: ">=0.45"         # the ast-grep versions its pattern rules work with
codeguard: ">=0.2"         # the codeguard versions that can load it
judge:
  model: claude-haiku-5-5  # the default for its judge rules; a binding may name another
```

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
`codeguard test` reports each rule without a why ([`--missing-why`](cli.md)).

## Judge rules

A judge rule is three files, all named by its id:

```
python/
  skills/<id>/SKILL.md       # the rule the judge checks
  bindings/<id>.yaml         # where it runs, when it runs, and the model that judges it
  rule-evals/<id>.yaml       # the rule eval: edits and the review each should get
```

The rule eval is what makes a rule trustworthy. It shows the rule flags the edits it
should and passes the ones it should, on the models that will judge it in reviews
([How the model resolves](judge-design.md#how-the-model-resolves)).

`codeguard eval` judges with the same model, unless `--provider` and `--model` name
another, as a package's CI does for its model matrix (the invariant that
[a rule passes whichever model a user picks](architecture.md#invariants)). The override
changes nothing a review judges with.

## Test a judge rule

1. `codeguard test` checks the triggers on every case, with no model call. It commits
   each `before` and `unchanged` file to a scratch repository, writes each `after`, and
   classifies the diff the way a review does.
2. `codeguard eval` reviews every case with the model a review would use: the binding's,
   else the project's default, else the package's, else the CLI's own default ([Which
   judge runs](configuration.md#which-judge-runs)), the way `codeguard review` would.
3. `codeguard eval --repeat 20` reviews each case twenty times, so an unstable verdict
   shows up as a failing run, named like `adds a second class [2/20]`.

[CLI](cli.md) lists `codeguard eval`'s options for judging part of a package, or with
another model. [What makes a case fail](rule-formats.md#what-makes-a-case-fail) lists
each command's failures.

An eval tests the rule, not the code, so it never uses
the verdict cache: every run calls the model. With a Logfire token each rule's run is
also in Logfire, as an experiment named `<rule> on <model>` with the provider, model,
confidence threshold, rule version (a hash of the skill, paths and triggers) and
codeguard version, so runs of the same rule compare.

A project tests the rules in its `.codeguard/` the same way a package does.
[Testing](testing.md#changing-a-rule-package) says which test each change needs and how
many runs it must pass.

## Package CI and releases

Run `codeguard test` and `codeguard eval` at the package root; they cover every ruleset.
A rule package's CI runs its model matrix with `codeguard eval --provider` and
`--model`, once for each model it supports.

Tag releases `v<major>.<minor>.<patch>`; projects name the tag as their `ref`.
[betterwithranch/codeguard-rules](https://github.com/betterwithranch/codeguard-rules) is
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
          packages-token: ${{ secrets.CODEGUARD_PACKAGES_TOKEN }}
```
