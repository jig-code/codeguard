# Write a rule package

A package is a git repo with a `codeguard-package.yaml` at its root:

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

## Bindings

A binding applies a rule to the files that match `paths` and none of `exclude_paths`.
A pattern rule's binding names its `rule`. A pattern rule without one runs on every file
in its language:

```yaml
rule: no-comments-in-tests
paths: ["**/test_*.py", "**/*_test.py", "**/tests/**/*.py", "**/conftest.py"]
```

Rule and gate ids are unique within a ruleset.

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
([Judge configuration](architecture.md#judge-configuration)).

`codeguard eval` judges with the same model, unless `--provider` and `--model` name
another, as a package's CI does for its model matrix (the invariant that
[a rule passes whichever model a user picks](architecture.md#invariants)). The override
changes nothing a review judges with.

### A rule in several languages

A judge rule's binding `paths` decide its languages: `["**/*.py", "**/*.ts"]` runs it on
Python and TypeScript files. A path names a language by its file extension; codeguard
knows javascript (`js`, `jsx`, `mjs`, `cjs`), python (`py`, `pyi`), ruby (`rb`) and
typescript (`ts`, `tsx`, `mts`, `cts`).

A path without an extension, like `src/**`, matches every language.

codeguard also loads a `<language>.md` beside `SKILL.md` as part of the rule, and fails
on one named after a language it doesn't know or the binding's paths don't match; the
[writing-rules skill](../skills/writing-rules/SKILL.md) says not to write one.

- When the paths name more than one language, `codeguard eval` reports each language
  apart, as `<id> (python)`, from the cases whose `file` is in that language, and each
  needs an `invalid` case.
- Triggers work per file: a change kind in any language, a gate only in its `language`.
  Only Python has change kinds and gates so far: on a file in another language, every
  trigger fires, and the judge is sent the changed lines without the code around them.

### The binding

A judge rule's binding names its `skill`, from the package root, and where and when it
runs:

```yaml
skill: python/skills/mock-only-at-boundary
paths: ["**/test_*.py", "**/*_test.py", "**/tests/**/*.py", "**/conftest.py"]
triggers: [mock-use]
```

`provider` and `model` are optional, each on its own: what a binding leaves out comes
from the project's or the package's default ([Configure the
judge](configuration.md#configure-the-judge)). Set them only for a rule whose eval passes on one model
alone ([a bound rule's judge model](configuration.md#configuration-reference)):

```yaml
provider: gemini                  # claude-cli, codex-cli, bedrock or gemini
model: gemini-3.1-pro-preview     # as the provider names it
```

A judge rule's id is its skill's directory name.

`triggers` names the code the rule's violations need. The judge skips a changed file
whose changed lines fall inside none of it. A binding without `triggers` gets `[any]`, so packages written before
triggers still load.

A trigger is a gate or a built-in change kind. A gate is an ast-grep rule in
`<ruleset>/gates/<id>.yml`, tested like a pattern rule by `rule-tests/<id>-test.yml`
(`invalid` cases are code the gate matches):

```yaml
id: mock-use
language: python
rule:
  kind: call
  has: {field: function, regex: "(^|\\.)(Mock|MagicMock|patch)$"}
```

A file touches a trigger when a changed line falls inside a node it matches. A new file
touches every trigger it matches. A blank line is never a changed line, in any language:
adding or removing blank lines fires no trigger, isn't judged and leaves no diagnostic,
so the blank line before a new method doesn't make its class part of the change. A line
holding only comments and docstrings touches only `comment` and `docstring`, not the
function or class around it: prose breaks no code rule. A rule
that needs every change says `triggers: [any]`; `codeguard test` warns on `any`, `code`,
`function-body` and `function-signature`. The built-in kinds are `comment`, `docstring`,
`import`, `function-signature`, `function-body`, `test-function`, `fixture`, `helper-function`,
`class-header`, `class-attribute`, `module-statement`, `annotation`, `call`,
`control-flow`, `return-yield`, `collection-literal`, `string-literal`,
`number-literal`, `attribute-access`, `subscript`, `conditional-expression`,
`membership-test`, `assert` and `raise`, plus three from the diff:
`definition-added-or-removed` (a def or class name added or removed), `code` (any line
that is not only a comment or docstring) and `any`. The syntax table in
`src/codeguard/syntax/languages/` defines each kind as an ast-grep rule.

### The rule eval

`rule-evals/<id>.yaml` (or `<id>.yml`, but not both) lists cases. Each case is an edit and
the review it should get:

- `name`: what the edit does, unique in the file.
- `inputs`: the edit. `before` is the file before it (leave it out for a new file),
  `after` is the file after it, and `file` is its path (default `module.py`), which
  must match the binding's paths. `unchanged` maps the path of each other file the
  edit needs, such as a package's `__init__.py`, to its text; the judge can read them,
  but they aren't part of the change, and can't include `file`. Every path is relative
  to the repository root, with no `..` or `./`, and outside `.git`.
- `expected_output`: the review's `outcome`, one of:
  - `invalid`: the triggers fire and the judge reports a violation;
  - `valid`: the triggers fire and the judge reports none;
  - `skipped`: the triggers don't fire, so the judge never sees the edit.

  A review whose only violations are below the confidence threshold has the outcome
  `uncertain`. No case can expect it: a case fails when the judge is uncertain about it.

  A case states no reason. The judge gives one with every verdict, and `codeguard eval`
  prints it for every case it judged, so whoever reads the eval sees on what ground the
  rule was decided; a wrong or vague reason shows where the rule's wording is unclear.

```yaml
cases:
  - name: adds a second class
    inputs:
      before: |
        class Order:
            pass
      after: |
        class Order:
            pass


        class Invoice:
            pass
    expected_output:
      outcome: invalid
  - name: defines one class
    inputs:
      after: |
        class Order:
            pass
    expected_output:
      outcome: valid
  - name: changes an attribute
    inputs:
      before: |
        class Order:
            total = 1
      after: |
        class Order:
            total = 2
    expected_output:
      outcome: skipped
```

`expected_output` can also list the `violations`, each with a `line`, `confidence` and
`message`, and optionally the `kinds` on its line; a violation without `kinds` isn't
checked on them.
A case that leaves them out checks only the outcome. Besides `cases`, the file may set
`name`, the rule id, which defaults to the file name; a rule has one eval file. The file
holds nothing else: codeguard decides how a case is judged and checked, so every rule is
held to the same bar.

### Test a judge rule

1. `codeguard test` checks the triggers on every case, with no model call. It commits
   each `before` and `unchanged` file to a scratch repository, writes each `after`, and
   classifies the diff the way a review does.
2. `codeguard eval` reviews every case with the binding's model, the way
   `codeguard review` would.
3. `codeguard eval --repeat 20` reviews each case twenty times, so an unstable verdict
   shows up as a failing run, named like `adds a second class [2/20]`.

[CLI](cli.md) lists `codeguard eval`'s options for judging part of a package, or with
another model.

An eval tests the rule, not the code, so it never uses
the verdict cache: every run calls the model. With a Logfire token each rule's run is
also in Logfire, as an experiment named `<rule> on <model>` with the provider, model,
confidence threshold, rule version (a hash of the skill, paths and triggers) and
codeguard version, so runs of the same rule compare.

### What makes a case fail

`codeguard test` fails a case when:

- its `file` is outside the binding's paths;
- its edit changes no code;
- it expects `invalid` or `valid` but the triggers miss the change, since a
  review would never judge it. The message lists the kinds the change touches;
- it expects `skipped` but the triggers fire. Narrow the gate until it passes, and keep
  every other case passing.

`codeguard eval` fails a case when:

- the review's outcome, or its violations when the case lists them, differ from
  `expected_output`. The message shows what the judge reported, its reason first;
- it expects `invalid` and the judge flags only lines outside the triggers. Reviews
  would miss that violation, so the message lists the kinds on those lines to add to
  `triggers`;
- the judge call fails, such as a quota error that outlasts the provider's retries. The
  other cases still run, so a passing eval means every case was judged.

A case counts only the violations a review would report: those on a changed or removed
line of the case's file.

`codeguard eval` also fails a judge rule with no `invalid` case, and a rule eval whose
id matches no judge rule. `codeguard eval` prints a table per rule, then the judge's
reason for each case it judged, then one line per failure.

### Where an eval's inputs come from

| Input | From |
|---|---|
| The edits, the files around them and their expected reviews | the rule eval, `rule-evals/<id>.yaml` |
| The convention | the skill |
| Paths and triggers | the binding |
| Provider and model | `--provider` and `--model`, else [Configure the judge](configuration.md#configure-the-judge) |
| The confidence threshold, and the Google Cloud project, location and calls at once | the caller's `.codeguard/config.yaml` |
| The judge prompt and how each case is checked | codeguard |

## Which test to write

A project tests the rules in its `.codeguard/` the same way a package does.
[Testing](testing.md#changing-a-rule-package) says which test each change needs and how
many runs it must pass.

Run `codeguard test` and `codeguard eval` at the package root; they cover every ruleset. Tag
releases `v<major>.<minor>.<patch>`; projects name the tag as their `ref`.
[betterwithranch/codeguard-rules](https://github.com/betterwithranch/codeguard-rules) is
an example.
