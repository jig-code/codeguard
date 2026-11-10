# Rule formats

The format of each file a rule is made of, in `.codeguard/` or a ruleset's directory
([Where rules live](write-rules.md#where-rules-live)). [Write rules](write-rules.md) says
how to write and test them.

## A pattern rule's binding

A binding applies a rule to the files that match `paths` and none of `exclude_paths`.
A pattern rule's binding names its `rule`. A pattern rule without one runs on every file
in its language:

```yaml
rule: no-comments-in-tests
paths: ["**/test_*.py", "**/*_test.py", "**/tests/**/*.py", "**/conftest.py"]
```

Rule and gate ids are unique within a ruleset.

## A judge rule's binding

A judge rule's binding names its `skill`, from the package root (in a project, from the
repository root, such as `.codeguard/skills/<id>`), and where and when it runs:

```yaml
skill: python/skills/mock-only-at-boundary
paths: ["**/test_*.py", "**/*_test.py", "**/tests/**/*.py", "**/conftest.py"]
triggers: [mock-use]
```

`provider` and `model` are optional, each on its own; [Choose a judge](judges.md) says
where one the binding leaves out comes from:

```yaml
provider: gemini                  # default: claude-cli; or codex-cli, gemini, bedrock
model: gemini-3.1-pro-preview     # default: the claude CLI's own; every provider but claude-cli needs one
```

A judge rule's id is its skill's directory name.

`triggers` names the code the rule's violations need. The judge skips a changed file
whose [changed lines](how-a-review-works.md#what-a-review-reports) fall inside none of it. A binding without `triggers` gets `[any]`, so packages written before
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

## A rule in several languages

A judge rule's binding `paths` decide its languages: `["**/*.py", "**/*.ts"]` runs it on
Python and TypeScript files. A path names a language by its file extension; codeguard
knows javascript (`js`, `jsx`, `mjs`, `cjs`), python (`py`, `pyi`), ruby (`rb`) and
typescript (`ts`, `tsx`, `mts`, `cts`).

A path without an extension, like `src/**`, matches every language.

codeguard also loads a `<language>.md` beside `SKILL.md` as part of the rule, after
`SKILL.md`, and fails on one named after a language it doesn't know or the binding's
paths don't match; the [writing-rules skill](../skills/writing-rules/SKILL.md) says not to
write one.

- When the paths name more than one language, `codeguard eval` reports each language
  apart, as `<id> (python)`, from the cases whose `file` is in that language, and each
  needs an `invalid` case.
- Triggers work per file: a change kind in any language, a gate only in its `language`.
  Only Python has change kinds and gates so far: on a file in another language, every
  trigger fires, and the judge is sent the changed lines without the code around them.

## The rule eval

`rule-evals/<id>.yaml` (or `<id>.yml`, but not both) lists cases. Each case is an edit and
the review it should get:

- `name`: the situation it tests, unique per file.
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
  - name: a second class added to the file
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
  - name: a file that defines one class
    inputs:
      after: |
        class Order:
            pass
    expected_output:
      outcome: valid
  - name: a change to an attribute
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
`message`, and optionally the `end_line` of the code that breaks the rule, which defaults
to its `line`, and the `kinds` on its lines; a violation without `kinds` isn't checked on
them.
A case that leaves them out checks only the outcome. Besides `cases`, the file may set
`name`, the rule id, which defaults to the file name; a rule has one eval file. The file
holds nothing else: codeguard decides how a case is judged and checked, so every rule is
held to the same bar.

## What makes a case fail

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

A case counts only the violations a review would report: those a changed line of the
case's file is part of ([What a review reports](how-a-review-works.md#what-a-review-reports)).

`codeguard eval` also fails a judge rule with no `invalid` case, and a rule eval whose
id matches no judge rule. `codeguard eval` prints a table per rule, then the judge's
reason for each case it judged, then one line per failure.

## Where an eval's inputs come from

| Input | From |
|---|---|
| The edits, the files around them and their expected reviews | the rule eval, `rule-evals/<id>.yaml` |
| The convention | the skill |
| Paths and triggers | the binding |
| Provider and model | the binding, or `--provider` and `--model` |
| The confidence threshold, and the Google Cloud project, location and calls at once | the caller's `.codeguard/config.yaml` |
| The judge prompt and how each case is checked | codeguard |
