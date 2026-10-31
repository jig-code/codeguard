# codeguard

Makes coding agents follow your project's coding conventions. Each convention is
written once, in the project, and applies wherever code is written or reviewed: while
Claude Code or Codex works, and in CI.

codeguard adds the checks a project's linters can't do. It doesn't replace or wrap
them.

## Add codeguard to a project

### Claude Code

In the project's `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "codeguard": {
      "source": {
        "source": "github",
        "repo": "jig-code/codeguard",
        "ref": "v0"
      }
    }
  },
  "enabledPlugins": {
    "codeguard@codeguard": true
  }
}
```

### Codex

List the plugin in the project's `.agents/plugins/marketplace.json`:

```json
{
  "name": "<project>",
  "plugins": [
    {
      "name": "codeguard",
      "source": {
        "source": "url",
        "url": "https://github.com/jig-code/codeguard.git",
        "ref": "v0"
      }
    }
  ]
}
```

### CI

```yaml
on: pull_request

jobs:
  codeguard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - uses: jig-code/codeguard@v0.9.1
        with:
          claude-code-oauth-token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
```

The action reviews the files changed since the merge base with the PR's base branch,
then runs the rule tests. The judge needs the token; create it with `claude setup-token`
and store it as a repository secret.

A judge call that couldn't complete fails the review, and no setting turns that off
([why](#configuration-reference)). To merge the PR anyway, add the
`codeguard-allow-judge-errors` label to it, so each bypass is chosen for one PR and
shows in its history. The action then passes
`--judge-errors-as-warnings` to the review, so those calls print as warnings, and rule
violations still fail. The label doesn't cover the `eval` input's `codeguard eval`,
which still fails on them.

Re-running the job doesn't pick up the label: a re-run reuses the event that started
the workflow, with the PR's labels at that time. For adding the label to start a new
review, and removing it to start a strict one, trigger on `labeled` and `unlabeled` for
that label only. Without the `if`, every label added to a PR re-runs the whole review and
its judge calls.

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened, labeled, unlabeled]

jobs:
  codeguard:
    if: >-
      (github.event.action != 'labeled' && github.event.action != 'unlabeled')
      || github.event.label.name == 'codeguard-allow-judge-errors'
```

Pin the action to a release tag, as above, and adopt each codeguard release in its own
PR ([Upgrade](#upgrade)), so a new release never changes a review without a change in
the project.

### Run formatters first

Format code before codeguard reviews it. A formatter that runs after the review changes
code that was never reviewed, and it changes the file, so the next review can't reuse
the cached verdict: it calls the model again and can reach a different verdict.

- In Claude Code, format each file when it's edited, in a `PostToolUse` hook on `Edit`
  and `Write`, not in a `Stop` hook: hooks on the same event run in parallel, so a
  formatter there can run after codeguard's review.
- In CI, run the format check before the codeguard step.
- Format an unformatted codebase in a commit of its own. Reformatted lines are changed
  lines, so formatting inside a feature change sends every one of them to the judge.

codeguard ignores added and removed blank lines, which change nothing in any language.
Other whitespace can change meaning, such as indentation in Python, so codeguard
leaves it to the formatter.

### Rules

A project's own rules live under `.codeguard/`. To write or change one, use the
plugin's `writing-rules` skill: it says which kind of rule fits a convention, how to
state the rule, and how to test it. This README documents the files and commands the
skill works with.

A rule is one of two kinds:

- A **pattern rule** is an ast-grep rule. It matches code by its syntax tree.
- A **judge rule** is a skill that Claude judges each change to a file against.

A project can also opt into rulesets from rule packages:

```yaml
# .codeguard/config.yaml
packages:
  - kind: git
    git: https://github.com/betterwithranch/codeguard-rules.git
    ref: v0.6.0
    rulesets:
      python:
        exclude: [no-del-param]
        rules:
          names-match-behavior:
            paths: ["src/**/*.py"]
            severity: warning
```

- Only the listed rulesets run.
- `include` lists the only rules that run, pattern and judged; rules the package adds
  later stay off. `exclude` turns rules off. Set one or the other.
- `rules.<id>` overrides a rule's `paths`, `exclude_paths`, `severity` or `ci_only`.
  `exclude_paths: []` brings back the files its binding leaves out. A judge rule's
  model can't be overridden: its evals pass on the model its binding names.
- `severity` on the ruleset sets every rule in it, including rules the package adds
  later; a rule's own `severity` override wins. Only `error` blocks Stop and fails CI,
  so `severity: warning` trials a package: its findings print without blocking. A
  failed judge call takes its rule's severity too.
- `ci_only: true` runs a rule in CI and in a `codeguard review` run by hand, but not in
  the agent's Stop hook. Set it on the ruleset or on one rule; a rule's own `ci_only`
  wins, as with `severity`. It exists for rules too costly to judge every time an agent
  stops, such as a judge rule that reads widely: each Stop hook review spends the
  developer's own Claude subscription, while CI reviews each push to a PR with the
  project's token.
  CI still fails the PR on the rule, so the agent meets it there instead of at Stop.
- An unknown ruleset or rule id is an error.
- `kind: path` with `path: ../my-rules` in place of `git` uses a local package, for
  working on one. To use it without editing the committed config, put that config in a
  gitignored file such as `codeguard.local.yaml` and set
  `CODEGUARD_CONFIG=codeguard.local.yaml`. The path is relative to the repository root.

Diagnostics name a packaged rule by package, ruleset and id:
`betterwithranch/python/no-del-param`.

A git package's `ref` is a tag or commit. Local and CI reviews use the rules at that
`ref`, so a commit gets the same rules everywhere, and a package release changes nothing
until a project moves its `ref`. To try a release, change `ref` locally, or point a
`kind: path` package at a checkout of it.

codeguard fetches each `ref` once into `~/.cache/codeguard/packages` and reuses it, so a
`ref` must not be a branch.

A project runs one ast-grep version for all its rules: codeguard's own, or the version
`.codeguard/config.yaml` sets, which runs through `uv tool run`:

```yaml
ast-grep: 0.45.3
```

codeguard fails when that version is outside a package's `ast-grep` range.

For a private package in CI, pass a token that can read it:

```yaml
      - uses: jig-code/codeguard@v0.9.1
        with:
          claude-code-oauth-token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
          packages-token: ${{ secrets.CODEGUARD_PACKAGES_TOKEN }}
```

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

### Bindings

A binding applies a rule to the files that match `paths` and none of `exclude_paths`.
A pattern rule's binding names its `rule`. A pattern rule without one runs on every file
in its language:

```yaml
rule: no-comments-in-tests
paths: ["**/test_*.py", "**/*_test.py", "**/tests/**/*.py", "**/conftest.py"]
```

Rule and gate ids are unique within a ruleset.

### Why a rule exists

Every rule says why it exists; the `writing-rules` skill says what to write and where.
`codeguard test` reports each rule without a why: as a warning by default, as a failure
with `--missing-why fail`, and not at all with `--missing-why off`.

### Judge rules

A judge rule is three files, all named by its id:

```
python/
  skills/<id>/SKILL.md       # the convention the judge checks
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

#### A rule in several languages

A judge rule's binding `paths` decide its languages: `["**/*.py", "**/*.ts"]` runs it on
Python and TypeScript files. A path names a language by its file extension; codeguard
knows javascript (`js`, `jsx`, `mjs`, `cjs`), python (`py`, `pyi`), ruby (`rb`) and
typescript (`ts`, `tsx`, `mts`, `cts`).

A language's forms of the convention go in a supplement beside the skill, named after
the language:

```
skills/<id>/
  SKILL.md                   # the convention, in no language's terms
  python.md                  # optional: the convention's forms in Python
  typescript.md
```

- The judge gets `SKILL.md`, then the supplement for the reviewed file's language, if
  there is one.
- A supplement named after no language codeguard knows, or after a language the
  binding's paths don't match, is an error. A path without an extension, like `src/**`,
  matches every language.
- A rule's version in a language covers `SKILL.md`, that language's supplement, its
  triggers and paths. A change to `SKILL.md` needs every language's eval to pass again;
  a change to a supplement, only its language's.
- When the paths name more than one language, `codeguard eval` reports each language
  apart, as `<id> (python)`, from the cases whose `file` is in that language, and each
  needs an `invalid` case.
- Triggers work per file: a change kind in any language, a gate only in its `language`.
  Only Python has change kinds and gates so far: on a file in another language, every
  trigger fires, and the judge is sent the changed lines without the code around them.

#### The binding

A judge rule's binding names its `skill`, from the package root, and where and when it
runs:

```yaml
skill: python/skills/mock-only-at-boundary
paths: ["**/test_*.py", "**/*_test.py", "**/tests/**/*.py", "**/conftest.py"]
triggers: [mock-use]
```

`provider` and `model` are optional. A binding that leaves them out is judged with
`claude-sonnet-5-5` through the `claude` CLI. Set them only to judge the rule with
something else:

```yaml
provider: gemini                  # default: claude-cli; or gemini, bedrock
model: gemini-3.1-pro-preview     # default: claude-sonnet-5-5; gemini and bedrock need one
```

A judge rule's id is its skill's directory name.

`triggers` names the code the rule's violations need. The judge skips a changed file
whose changed lines fall inside none of it, and is sent the whole of each trigger node
around a change. A binding without `triggers` gets `[any]`, so packages written before
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

#### The rule eval

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

#### Test a judge rule

1. `codeguard test` checks the triggers on every case, with no model call. It commits
   each `before` and `unchanged` file to a scratch repository, writes each `after`, and
   classifies the diff the way a review does.
2. `codeguard eval` reviews every case with the binding's model, the way
   `codeguard review` would.
3. `codeguard eval --repeat 20` reviews each case twenty times, so an unstable verdict
   shows up as a failing run, named like `adds a second class [2/20]`.

`codeguard eval` takes options to judge part of a package, or with another model:

- `--rule <id>` evaluates only that judge rule; repeat it for more. The check for an
  eval with an `invalid` case covers only the rules selected.
- `--case <text>` judges only the cases whose name contains the text; repeat it to
  judge the cases matching any of them. A rule with no matching case is left out.
- `--provider claude-cli`, `--provider gemini` or `--provider bedrock` judges every
  selected rule with that provider instead of its binding's. `--model` names the model;
  it defaults to `claude-sonnet-5-5` for `claude-cli`, `gemini-3.1-pro-preview` for
  `gemini` and `us.anthropic.claude-haiku-5-5` for `bedrock`.

A `--rule` that names no judge rule, or a `--case` that no selected rule's case name
contains, fails the eval before any case is judged.

```sh
codeguard eval --rule mock-only-at-boundary --case "patches a" --repeat 20
codeguard eval --provider gemini --repeat 20
```

Both take a package directory, so `codeguard eval path/to/package` evaluates a package
outside the current repository. An eval tests the rule, not the code, so it never uses
the verdict cache: every run calls the model. With a Logfire token each rule's run is
also in Logfire, as an experiment named `<rule> on <model>` with the provider, model,
confidence threshold, rule version (a hash of the skill, paths and triggers) and
codeguard version, so runs of the same rule compare.

#### What makes a case fail

`codeguard test` fails a case when:

- its `file` is outside the binding's paths;
- its edit changes no code;
- it expects `invalid` or `valid` but the triggers miss the change, since a
  review would never judge it. The message lists the kinds the change touches;
- it expects `skipped` but the triggers fire. Narrow the gate until it passes, and keep
  every other case passing.

`codeguard eval` fails a case when:

- the review's outcome, or its violations when the case lists them, differ from
  `expected_output`. The message shows what the judge reported;
- it expects `invalid` and the judge flags only lines outside the triggers. Reviews
  would miss that violation, so the message lists the kinds on those lines to add to
  `triggers`;
- the judge call fails, such as a quota error that outlasts the provider's retries. The
  other cases still run, so a passing eval means every case was judged.

A case counts only the violations a review would report: those on a changed or removed
line of the case's file.

`codeguard eval` also fails a judge rule with no `invalid` case, and a rule eval whose
id matches no judge rule. `codeguard eval` prints a table per rule, then one line per
failure.

#### Where an eval's inputs come from

| Input | From |
|---|---|
| The edits, the files around them and their expected reviews | the rule eval, `rule-evals/<id>.yaml` |
| The convention | the skill |
| Paths and triggers | the binding |
| Provider and model | the binding, or `--provider` and `--model` |
| The confidence threshold, and the Google Cloud project, location and calls at once | the caller's `.codeguard/config.yaml` |
| The judge prompt and how each case is checked | codeguard |

### Which test to write

A project tests the rules in its `.codeguard/` the same way a package does.

| You add or change | Write | It checks | Run | Calls the model |
|---|---|---|---|---|
| A pattern rule or gate | `rule-tests/<id>-test.yml` | the rule matches its `invalid` cases and none of its `valid` ones | `codeguard test` | no |
| A judge rule's skill, binding or `triggers` | `rule-evals/<id>.yaml` | the triggers fire on each edit but the `skipped` ones | `codeguard test` | no |
| | | each edit gets its expected review, 20 runs of 20 | `codeguard eval --repeat 20` | yes |

Run `codeguard test` and `codeguard eval` at the package root; they cover every ruleset. Tag
releases `v<major>.<minor>.<patch>`; projects name the tag as their `ref`.
[betterwithranch/codeguard-rules](https://github.com/betterwithranch/codeguard-rules) is
an example.

## Setup

The plugin is codeguard: it ships the CLI and runs it with
[uv](https://docs.astral.sh/uv/getting-started/installation/), so uv is all anyone
working in the project installs. The first review after an install or upgrade takes a
little longer while uv builds codeguard's environment in the plugin's data directory.

In Claude Code, install the plugin. Project settings enable it but don't install it.

```sh
claude plugin install codeguard@codeguard --scope project
```

In Claude Code, the plugin also puts `codeguard` on the PATH of the commands Claude
runs, for skills such as writing a rule.

In Codex, trust codeguard's hooks in `/hooks`. Codex doesn't give plugins a command, so
writing rules there needs the CLI on its own.

### The CLI on its own

To run codeguard from a terminal, or to write rules in Codex, install the CLI with uv.
It doesn't need the plugin, and the plugin doesn't need it.

```sh
uv tool install git+https://github.com/jig-code/codeguard@v0
```

### Upgrade

Pin in CI, auto-update in your dev environment. A commit on `main` reaches no one until
it is released.

**Pin in CI.** A project adopts each codeguard release and each rule package tag in its
own PR, so whatever the upgrade changes in reviews and rule tests shows up there and
nowhere else:

- Move the action's tag (`jig-code/codeguard@v<version>`, and `jig-code/codeguard/test@v<version>`
  if the project defines rules) to the new release.
- Move a rule package's `ref` in `.codeguard/config.yaml` to its new tag.

**Auto-update in your dev environment**, so you meet a release's changes before CI does:
turn on auto-update for the codeguard marketplace in `/plugin` (Marketplaces, then
codeguard). Auto-update is off by default for marketplaces outside Anthropic's own. It
applies new releases in the background, and they take effect in the next session. If a
release breaks a branch you're working on, turn auto-update off until the fix ships. To
update by hand, run these, then `/reload-plugins` or start a new session:

```sh
claude plugin marketplace update codeguard
claude plugin update codeguard@codeguard --scope project
```

Upgrade the CLI with `uv tool upgrade codeguard`, if you installed it.

## What the hooks check

When an agent or subagent stops, the hook runs `codeguard review` in its working
directory: the uncommitted and untracked files, whoever changed them and however. Start
the session in the repository's directory and make changes from there. Claude Code reads a
project's hooks only from the directory a session starts in, and a cloud session over several
repositories starts above them, where no repository's hooks run. It runs the codeguard
the plugin ships, not one on your PATH. Claude Code and Codex get the same behaviour.

- An error blocks the stop, and only errors reach the agent. It blocks every time the
  agent stops until the errors are fixed. When the agent can't fix one, interrupt it
  and fix the rule.
- Everything else goes to you, not the agent: warnings, findings below the confidence
  threshold, and rules the judge couldn't check (a failed `claude` call or the time
  limit). The hook passes `--judge-errors-as-warnings`, since the agent can't fix those;
  CI still fails on them unless the PR has the `codeguard-allow-judge-errors` label.
- Rules the config marks `ci_only` don't run: the hook passes `--skip-ci-only`. CI
  doesn't, so they still run there ([Rules](#rules)).
- If the review crashes or uv can't build codeguard's environment, you see why, and the
  stop goes through.

In Claude Code, a second hook guards the rules themselves. Before an `Edit` or `Write` to
a rule file (a skill, pattern rule, gate, binding, rule test or rule eval, under
`.codeguard/` or a package ruleset's directory), it checks the session's transcript for
the `writing-rules` skill: a Skill call naming it, or a Read of its `SKILL.md`. Until the
session has loaded it, the edit is denied with a message telling the agent to load it. A
transcript the hook can't read lets the edit through.

The judge gets the code the change touched: each changed function or method, with its
decorators; each changed statement outside them, whole, with the header and decorators of
the class it's in; for a changed `elif`, `else`, `except` or `finally` line, just that
clause, with the `try` block an `except` guards; each class whose header changed, whole;
each changed comment or docstring line alone; and, for each of the rule's
triggers, the whole of each node of that kind around a changed line of code, so the judge
sees the code that made the rule apply. Removed lines are sent with the code the change
kept around them, the same way: the function or method they were in, the header of their
class, the rest of a statement they were part of, or the header of the statement whose
block they were in (for a removed `except`, its `try` and the block it guarded), never the
code beside them. A renamed file is compared with the file it was renamed from. Unless
a class's header changed, its other members aren't sent, though the judge can read them.
What is sent is what the judge has to read to decide; anything it only might need, it
reads itself.
Lines carry the file's line numbers; added and changed lines are marked `+`, and the
lines git's diff shows the change removed are marked `-`. A new file is sent whole but
for its blank lines outside a function or method; every file with `--all` is sent whole,
all of it marked changed. The judge reads the rest of the file, or any other file in the
repository, with its read-only tools.

A review reports only violations a changed or removed line is part of, on that line. What the line
held before doesn't matter: editing a line that already broke a rule reports it, so code
a change touches is left better than it was found. Untouched code isn't reported, even in
the function or class around the change: adding a line to a method doesn't report the
method's name, and renaming a variable doesn't report the class's design. A changed line
that breaks a rule together with the code around it is reported, such as a method that
gives its class another responsibility. Other functions and classes in the file, and the
other blocks of a statement around the change, such as the `except` of a `try` whose
body changed, are read as context but never reported. A verdict is cached until the changed code, the
rest of the file, the rule, the model, or a file the judge loaded changes. A loaded file
is one the judge read, or one its searches returned: a file a grep matched or a glob
listed. A file a search would only start returning later doesn't count.

The judge rates its confidence in each violation from 0 to 1. An error below the
threshold is reported as a warning, with its confidence, and doesn't block. The
threshold defaults to 0.9; set it in `.codeguard/config.yaml`:

```yaml
confidence_threshold: 0.8
```

A judged diagnostic prints its confidence, so a warning shows how far it fell short:

```
app/orders.py:12: warning no-pre-derived-arguments: The call passes both lines and the context they come from. (confidence 0.70) [3f1c9a2b7d40]
```

A review stops judging after 5 minutes. Each rule and file it didn't judge gets a
`judge_error` diagnostic at the rule's severity, so an unchecked `error` rule fails the
review. A failed judge call does the same.
The GitHub Action stops the review 2 minutes after the limit, in case it hangs. Change the
limit in `.codeguard/config.yaml`:

```yaml
review_time_limit_minutes: 10
```

In a review, each judge rule is judged with its binding's provider and model, the same
ones its rule eval passed on; see [Judge rules](#judge-rules). A binding that sets neither is judged
with `claude-sonnet-5-5` through the `claude` CLI.

### Judge with Gemini on Google Cloud

By default the judge runs `claude -p`. A judge rule whose binding sets
`provider: gemini` is judged with Gemini on Google Cloud (Vertex AI) instead, in reviews
and in its rule eval, so its rule eval has to pass on Gemini. `codeguard eval --provider
gemini` judges a rule's eval with Gemini whatever its binding names:

```yaml
skill: .claude/skills/responsibility-placement
paths: ["app/**/*.py"]
provider: gemini
model: gemini-3.1-pro-preview
```

`judge` in `.codeguard/config.yaml` sets where Gemini runs and how many calls run at once:

```yaml
judge:
  project: my-project             # default: GOOGLE_CLOUD_PROJECT
  location: global                # default: GOOGLE_CLOUD_LOCATION
  calls_at_once: 2                # default: 2 for gemini, one per CPU for claude-cli
```

Gemini reads the working directory through read-only `read_file`, `grep` and `glob`
tools, limited to the repository, thinks at the `LOW` level, and returns its verdict as
structured output with the same verdict schema as Claude. A judgement that makes 10
requests without a verdict is reported as not judged. Verdicts are cached per provider
and model, so switching providers doesn't reuse Claude's verdicts.

Gemini's pay-as-you-go capacity is shared and limited by tokens per minute, so the
gemini provider makes 2 calls at once. Each provider has its own limit, so Claude and
Gemini rules in one review don't wait on each other. A request that Gemini turns away
(408, 429 or a 5xx) or whose connection breaks is sent again for about 15 seconds, and
then the rule is reported as not judged.

Use `gemini-3.1-pro-preview`, the Gemini model codeguard was tested with. Flash was
unreliable in testing. Gemini 4 Argon was as accurate, but some of its requests took 15
to 37 s, where 3.1 Pro's longest of 79 took 13 s (median 6.5 s).

`provider: bedrock` judges with Claude on Amazon Bedrock through the same tools, for a
run that must be Claude. boto3 finds the credentials and region (`AWS_DEFAULT_REGION`)
as the AWS CLI does, and the model is a Bedrock inference profile such as
`us.anthropic.claude-haiku-5-5`.

codeguard signs in with Application Default Credentials. Set it up once per project:

1. Enable the Vertex AI API:
   `gcloud services enable aiplatform.googleapis.com --project my-project`.
2. Create a service account with the Vertex AI User role:
   ```sh
   gcloud iam service-accounts create codeguard --project my-project
   gcloud projects add-iam-policy-binding my-project \
     --member serviceAccount:codeguard@my-project.iam.gserviceaccount.com \
     --role roles/aiplatform.user
   ```
3. Give codeguard the credentials. On your machine, `gcloud auth application-default login`
   is enough. Elsewhere, create a key with
   `gcloud iam service-accounts keys create key.json --iam-account codeguard@my-project.iam.gserviceaccount.com`
   and set `GOOGLE_APPLICATION_CREDENTIALS` to its path. In GitHub Actions, use
   `google-github-actions/auth` before the codeguard action.

Where a proxy adds credentials to requests, as Claude Code cloud environments' network
secrets do, use an API key bound to the service account instead: create it under
**APIs & Services → Credentials** with only Agent Platform API allowed, have the proxy send
it as the `x-goog-api-key` header to `aiplatform.googleapis.com`, and set
`GOOGLE_API_KEY=proxy-injected` with `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`,
`project` and `location` unset. The key identifies the project.

## Telemetry

Set `LOGFIRE_TOKEN` to a Logfire write token and codeguard sends a trace of each run.
Without it, codeguard sends nothing. Set it where the agent runs: your shell profile, or
`env` in `~/.claude/settings.json`.

- `claude judges {rule} on {file}`: one span per Claude call, with `model`, `num_turns`,
  `duration_ms`, `cost_usd`, `input_tokens`, `output_tokens`, `cache_read_input_tokens`,
  `cache_creation_input_tokens`, `thinking_tokens` and `tool_calls`.
- `gemini judges {rule} on {file}`: one span per Gemini judgement, with `model`,
  `num_turns`, `input_tokens`, `output_tokens`, `cache_read_input_tokens` and
  `thinking_tokens`, summed over its requests, and `tool_calls`. Its time starts once the call has a slot,
  not while it waits for one. Inside it, Pydantic AI's spans record each request and
  tool call with its content: the prompt, which holds the convention and the changed
  code, Gemini's thought summaries, the files it read and its verdict.
- `tool_calls` on a Claude or Gemini span is each call the judge made to its read-only
  tools, in order: the tool's name and the arguments it gave, such as the path it read or
  the pattern it searched for. It records a call that failed, and on Gemini, the calls of
  a judgement that returned no verdict. Claude's call that returns the verdict isn't one.
- `judge {rule} on {file}`: one span per rule and file, with `cache_hit`, `violations`,
  `loaded_files` (the files the verdict depends on) and `changed_files` (the loaded files
  that changed since the cached verdict, which is why it was judged again). The Claude or
  Gemini span inside it has that judgement's time and tokens.
- `review {repository}`: `files`, `diagnostics`, `errors`, and `host` (the caller passed
  with `--host`, such as `claude-code` or `codex`).

In CI, pass the token as the action's `logfire-token` input.

## Configuration reference

A project's settings live in `.codeguard/config.yaml`, which is committed, so a commit
gets the same review on every machine and in CI. Every setting is optional.

| Setting | Default | What it does | Why the default |
|---|---|---|---|
| `confidence_threshold` | `0.9` | A judged `error` with a lower confidence is reported as a warning, to you rather than the agent, and doesn't block. | Only findings the judge is sure of should stop an agent or fail a PR. A doubtful finding that blocked would send the agent after a violation that may not exist. See [What the hooks check](#what-the-hooks-check). |
| `review_time_limit_minutes` | `5` | The review stops judging after this long. Each rule and file it didn't judge is reported as not checked, at the rule's severity. The GitHub Action stops the review 2 minutes after it. | A stuck `claude` call once hung a CI review for 30 minutes with no output. A limit turns a hang into a visible failure. |
| `ast-grep` | the version codeguard installs | The ast-grep version every pattern rule and gate runs with, through `uv tool run`. | One version for every rule, so a rule matches the same code on every machine. codeguard fails when it is outside a package's `ast-grep` range. |
| `packages` | none | The rule packages and rulesets the project uses; see [Rules](#rules). Without it, only the rules in `.codeguard/` run. | A project opts into each ruleset, so no rule runs that the project didn't choose. |
| `packages[].rulesets.<name>.include` | every rule in the ruleset | The only rules that run. Rules the package adds later stay off. Set it or `exclude`, not both. | |
| `packages[].rulesets.<name>.exclude` | none | Rules that don't run. | |
| `packages[].rulesets.<name>.severity` | each rule's own | The severity of every rule in the ruleset, including rules the package adds later. A rule's own override wins. | `warning` trials a ruleset: its findings print without blocking. |
| `packages[].rulesets.<name>.ci_only` | `false` | Runs every rule in the ruleset only in CI and in reviews run by hand, not in the agent's Stop hook. A rule's own override wins. | A hook review spends the developer's subscription each time an agent stops; `true` keeps a costly rule to CI. See [Rules](#rules). |
| `packages[].rulesets.<name>.rules.<id>` | the binding's | Overrides a rule's `paths`, `exclude_paths`, `severity` or `ci_only`. | |
| `judge.calls_at_once` | one per CPU for `claude-cli`, `2` for `gemini` | How many judge calls run at once. | A `claude` call mostly waits on the network, so the limit follows the machine. Gemini's pay-as-you-go capacity is shared, so fewer calls keep a review under its tokens-per-minute limit. |
| `judge.project`, `judge.location` | `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` | Where Gemini runs; see [Judge with Gemini on Google Cloud](#judge-with-gemini-on-google-cloud). | |

Two things have no setting on purpose:

- **Judge errors fail the review.** A judge call that couldn't complete, including one
  cut off by the time limit, is reported at its rule's severity, so for an `error` rule
  it fails CI. A rule the judge couldn't check is code nobody checked, and a warning in
  a passing check goes unseen: if a setting could turn these into warnings for a
  project, a broken judge, an expired token or a codeguard bug would let every PR
  through. A bypass is always for one PR: the `codeguard-allow-judge-errors` label
  ([CI](#ci)), which shows in the PR's history. The Stop hook always passes
  `--judge-errors-as-warnings`, because the agent can't fix a judge failure. It shows
  the failure to you, and CI still fails on it.
- **A rule's judge model.** A judge rule is judged with the model its binding names, the
  one its rule eval passed on. A project can't switch it to a model the eval never ran
  on.

Settings that decide what a review reports belong in the committed config, not in the
environment, so CI and every machine review a commit the same way. Environment variables
only choose the config file or the codeguard to run, sign the judge in, or turn on
telemetry:

| Variable | Default | What it does |
|---|---|---|
| `CODEGUARD_CONFIG` | `.codeguard/config.yaml` | The config file to load, relative to the repository root, such as a gitignored `codeguard.local.yaml` for working on a local package. |
| `CODEGUARD` | the codeguard the plugin ships | The codeguard the hooks run instead, such as a checkout's `.venv/bin/codeguard`. |
| `CLAUDE_CODE_OAUTH_TOKEN` | the `claude` CLI's own sign-in | The subscription token the judge runs with, in CI. |
| `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` | unset | Where Gemini runs, for a `gemini` binding, unless `judge.project` and `judge.location` set it; see [Judge with Gemini on Google Cloud](#judge-with-gemini-on-google-cloud). |
| `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_API_KEY` | Application Default Credentials | How Gemini signs in: a service account key file, or an API key a proxy adds. |
| `LOGFIRE_TOKEN` | none: nothing is sent | Sends a trace of each run to Logfire; see [Telemetry](#telemetry). |

## CLI

| Command | Who runs it | What it checks | Calls the model |
|---|---|---|---|
| `codeguard review` | a project using codeguard: the agent's Stop hook, and the action in CI | the project's changed code against the rules it opts into | for judge rules |
| `codeguard test` | whoever writes rules, in a rule package or a project's `.codeguard/` | the rules: pattern rules and gates match their test cases, and judge rules' triggers fire on their eval cases | no |
| `codeguard eval` | whoever writes rules | judge rules: each eval case gets its expected review | yes |

`review` checks code; `test` and `eval` check the rules themselves. [Write a rule
package](#write-a-rule-package) covers `test` and `eval`.

From the project:

```sh
codeguard review              # uncommitted changes
codeguard review --base main  # changes since the merge base with main
codeguard review --all        # every file
codeguard review --dry-run    # pattern rules, then count the judge calls; calls no model
codeguard review --format json  # one JSON object with every diagnostic
codeguard review --judge-errors-as-warnings  # judge calls that couldn't complete don't fail
codeguard review --skip-ci-only  # skip ci_only rules, as the Stop hook does
codeguard test                # pattern rule and gate tests, and judge rule eval triggers
codeguard test --update-all   # the same, regenerating snapshots
codeguard eval                # judge rule evals; calls the configured judge
```

## Working on codeguard

[docs/testing.md](docs/testing.md) says how to test a change to codeguard, a rule
package or an app.

Tests:

```sh
uv run pytest
```

`uv run pytest` runs offline: it calls no model. The LLM tests check that the judge's
instructions, request and tools still get the right verdicts from a real model. Each
one reviews an edit in a scratch repository the way `codeguard review` does, with the
fixture bindings' judge, `gemini-3.1-pro-preview` on Vertex AI, so they need Gemini
credentials (Judge with Gemini on Google Cloud, above) and cost tokens. They are marked
`llm`, which plain `pytest` deselects. CI signs in with the repository's
`GOOGLE_CREDENTIALS` secret, a service account key with the Vertex AI User role, and
its `GOOGLE_CLOUD_PROJECT` variable. `--judge-provider` and `--judge-model` judge them
with another model, as `codeguard eval --provider` does: `--judge-provider bedrock` runs
them on Haiku on Bedrock. CI runs them; run them after changing the judge's instructions, request or
tools:

```sh
uv run pytest -m llm -n 4    # each case 3 times, as CI does
```

`-n 4` runs four tests at once, each making up to 2 Gemini calls at once. It only saves
time: any number gives the same result, though more may hit Gemini's tokens-per-minute
limit. [docs/testing.md](docs/testing.md) says which to run for a
change.

Their fixtures are the cases in `evals/judge/python/rule-evals/`, with the skills and
bindings beside them. When a case flips between runs or comes back uncertain, follow the
`writing-rules` skill, and look at the judge prompt as well. The plain suite checks each
case's triggers.

The `writing-rules` skill has its own evals in `evals/writing-rules/`;
[docs/skill-evals.md](docs/skill-evals.md) says how to run and write them.

Run the CLI from this clone. `--editable` links the tool to the source, so edits
apply on the next run; reinstall only after changing dependencies:

```sh
uv tool install --editable .
```

Point a project's hooks at this clone.

- Claude Code: in the project's `.claude/settings.local.json`, declare the marketplace
  as a directory. It replaces the GitHub entry by name, for you only.
  ```json
  {
    "extraKnownMarketplaces": {
      "codeguard": {
        "source": { "source": "directory", "path": "/path/to/codeguard" }
      }
    }
  }
  ```
  Python edits apply on the next hook run. Edits to `hooks.json` or `plugin.json`
  need `/reload-plugins`.

  This clone's own `.claude/settings.json` runs its hooks with `.venv/bin/codeguard`, the
  build `uv sync` keeps current. `CODEGUARD=<path>` makes the hook run any other build.
- Codex:
  ```sh
  codex plugin marketplace add /path/to/codeguard
  codex plugin add codeguard@codeguard
  ```
  Run `codex plugin add` again after each edit.

## Release

Release when a change on `main` should reach the projects using codeguard, or when a
rule package needs it (a package's `codeguard` range is checked against the CLI's
version). Engineers get only released versions; see [Upgrade](#upgrade).

1. Bump the version to the same `<version>` in all three files, in the PR with the
   change or in a PR of its own:
   - `version` in `pyproject.toml`, which rule packages' `codeguard` ranges are checked
     against;
   - `version` in `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`.
     Claude Code installs a plugin update only when this changes, so a release with
     the old version reaches no one.

   CI fails a PR whose three versions differ.
2. Validate:
   ```sh
   claude plugin validate .
   ```
3. Once it is merged, tag the merge commit and push the tag:
   ```sh
   git fetch origin main
   git tag v<version> origin/main
   git push origin v<version>
   ```
   The release workflow checks that the tag matches all three versions, then moves
   the major tag (`v0`) to the release. If it fails, fix the versions on `main`, then
   move the tag to the fixed commit and push it again:
   ```sh
   git tag --force v<version> origin/main
   git push --force origin v<version>
   ```
