# Add codeguard to a project

The plugin is codeguard: it ships the CLI and runs it with
[uv](https://docs.astral.sh/uv/getting-started/installation/), so uv is all anyone
working in the project installs. The first review after an install or upgrade takes a
little longer while uv builds codeguard's environment in the plugin's data directory.

## Claude Code

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

Then install the plugin. Project settings enable it but don't install it.

```sh
claude plugin install codeguard@codeguard --scope project
```

## Codex

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

Then trust codeguard's hooks in `/hooks`.

## CI

```yaml
on: pull_request

jobs:
  codeguard:
    runs-on: ubuntu-latest
    env:
      CODEGUARD_JUDGE__PROVIDER: bedrock
      CODEGUARD_JUDGE__MODEL: ${{ vars.CODEGUARD_JUDGE_MODEL }}
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ vars.CODEGUARD_AWS_ROLE }}
          aws-region: us-east-1
      - uses: jig-code/codeguard@v0.11.0
```

The action reviews the files changed since the merge base with the PR's base branch,
then runs the rule tests. The job's `CODEGUARD_JUDGE__PROVIDER` and
`CODEGUARD_JUDGE__MODEL` name its judge: Claude on Amazon Bedrock with the job's AWS
credentials, as in the example, or Gemini on Vertex AI with `google-github-actions/auth`
([Choose a judge](judges.md)). [Which judge runs](configuration.md#which-judge-runs) says
how those variables and the project's config combine.

A judge call that couldn't complete fails the review, and no setting turns that off
([why](configuration.md#no-setting-on-purpose)). To merge the PR anyway, add the
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

## Opt into a rule package

A project's own rules live under `.codeguard/`, in the layout
[Write a rule package](rule-packages.md) describes. To write or change one, use the
plugin's [writing-rules skill](../skills/writing-rules/SKILL.md). The two kinds of rule
are in [Rules](architecture.md#rules).

A project can also opt into rulesets from rule packages. List the rulesets to run every
rule in each:

```yaml
# .codeguard/config.yaml
packages:
  - kind: git
    git: https://github.com/betterwithranch/codeguard-rules.git
    ref: v0.6.0
    rulesets: [general, python]
```

To choose a ruleset's rules or change how they run, give it settings instead
([Rule package keys](configuration.md#rule-package-keys) says what each does):

```yaml
    rulesets:
      python:
        exclude: [no-del-param]
        rules:
          names-match-behavior:
            paths: ["src/**/*.py"]
            severity: warning
```

`kind: path` with `path: ../my-rules` in place of `git` uses a local package, for
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

For a private package in CI, pass a token that can read it:

```yaml
      - uses: jig-code/codeguard@v0.11.0
        with:
          packages-token: ${{ secrets.CODEGUARD_PACKAGES_TOKEN }}
```

## Run formatters first

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

## The CLI on its own

[Claude Code](#claude-code) and [Codex](#codex) install the plugin. Codex doesn't give
plugins a command, so writing rules there needs the CLI on its own.

To run codeguard from a terminal, or to write rules in Codex, install the CLI with uv.
It doesn't need the plugin, and the plugin doesn't need it.

```sh
uv tool install git+https://github.com/jig-code/codeguard@v0
```

## Upgrade

Pin in CI, auto-update in your dev environment. A commit on `main` reaches no one until
it is released.

**Pin in CI.** A project adopts each codeguard release and each rule package tag in its
own PR, so whatever the upgrade changes in reviews and rule tests shows up there and
nowhere else:

- Move the action's tag (`jig-code/codeguard@v<version>`) to the new release.
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
