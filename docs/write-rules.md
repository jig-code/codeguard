# Write rules

## Write a rule package

A package is a git repo with a `codeguard-package.yaml` at its root:

```yaml
name: betterwithranch
rulesets: [python]
ast-grep: ">=0.45"         # the ast-grep versions its pattern rules work with
codeguard: ">=0.2"         # the codeguard versions that can load it
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

### Why a rule exists

Every rule says why it exists; the `writing-rules` skill says what to write and where.
`codeguard test` reports each rule without a why: as a warning by default, as a failure
with `--missing-why fail`, and not at all with `--missing-why off`.

### Judge rules

A judge rule is three files, all named by its id:

```
python/
  skills/<id>/SKILL.md       # the rule the judge checks
  bindings/<id>.yaml         # where it runs, when it runs, and the model that judges it
  rule-evals/<id>.yaml       # the rule eval: edits and the review each should get
```

The rule eval is what makes a rule trustworthy. It shows the rule flags the edits it
should and passes the ones it should, on the model that will judge it in reviews. In
reviews, that model is the binding's, and nothing overrides it: a project can't switch a
rule to a model its rule eval never passed on. To move a rule to another model, change
its binding and pass its rule eval again.

`codeguard eval` judges with the binding's model too, unless `--provider` names another.
That is for a package whose bar is passing on more than one model, such as a CI job per
provider; it changes nothing a review judges with.

#### Test a judge rule

1. `codeguard test` checks the triggers on every case, with no model call. It commits
   each `before` and `unchanged` file to a scratch repository, writes each `after`, and
   classifies the diff the way a review does.
2. `codeguard eval` reviews every case with the binding's model, the way
   `codeguard review` would.
3. `codeguard eval --repeat 3` reviews each case three times, so an unstable verdict
   shows up as a failing run, named like `a second class added to the file [2/3]`.

`codeguard eval` takes options to judge part of a package, or with another model:

- `--rule <id>` evaluates only that judge rule; repeat it for more. The check for an
  eval with an `invalid` case covers only the rules selected.
- `--case <text>` judges only the cases whose name contains the text; repeat it to
  judge the cases matching any of them. A rule with no matching case is left out.
- `--provider claude-cli`, `--provider codex-cli`, `--provider gemini` or `--provider bedrock` judges every
  selected rule with that provider instead of its binding's. `--model` names the model;
  it defaults to `claude-sonnet-5-5` for `claude-cli`, `gpt-6-luna` for `codex-cli`, `gemini-3.1-pro-preview` for
  `gemini` and `us.anthropic.claude-haiku-5-5` for `bedrock`.

A `--rule` that names no judge rule, or a `--case` that no selected rule's case name
contains, fails the eval before any case is judged.

```sh
codeguard eval --rule mock-only-at-boundary --case "a patch" --repeat 3
codeguard eval --provider gemini --repeat 3
```

Both take a package directory, so `codeguard eval path/to/package` evaluates a package
outside the current repository. An eval tests the rule, not the code, so it never uses
the verdict cache: every run calls the model. With a Logfire token each rule's run is
also in Logfire, as an experiment named `<rule> on <model>` with the provider, model,
confidence threshold, rule version (a hash of the skill, paths and triggers) and
codeguard version, so runs of the same rule compare.

### Which test to write

A project tests the rules in its `.codeguard/` the same way a package does.

| You add or change | Write | It checks | Run | Calls the model |
|---|---|---|---|---|
| A pattern rule or gate | `rule-tests/<id>-test.yml` | the rule matches its `invalid` cases and none of its `valid` ones | `codeguard test` | no |
| A judge rule's skill, binding or `triggers` | `rule-evals/<id>.yaml` | the triggers fire on each edit but the `skipped` ones | `codeguard test` | no |
| | | each edit gets its expected review, 3 runs of 3 | `codeguard eval --repeat 3` | yes |

Run `codeguard test` and `codeguard eval` at the package root; they cover every ruleset. Tag
releases `v<major>.<minor>.<patch>`; projects name the tag as their `ref`.
[betterwithranch/codeguard-rules](https://github.com/betterwithranch/codeguard-rules) is
an example.

## Try a local package

- `kind: path` with `path: ../my-rules` in place of `git` uses a local package, for
  working on one. To use it without editing the committed config, put that config in a
  gitignored file such as `codeguard.local.yaml` and set
  `CODEGUARD_CONFIG=codeguard.local.yaml`. The path is relative to the repository root.

## A private package

For a private package in CI, pass a token that can read it:

```yaml
      - uses: jig-code/codeguard@v0.9.1
        with:
          claude-code-oauth-token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
          packages-token: ${{ secrets.CODEGUARD_PACKAGES_TOKEN }}
```
