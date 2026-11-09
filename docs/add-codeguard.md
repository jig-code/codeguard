# Add codeguard to a project

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

A project can also opt into rulesets from rule packages. List the rulesets to run every
rule in each:

```yaml
# .codeguard/config.yaml
packages:
  - kind: git
    git: https://github.com/betterwithranch/codeguard-rules.git
    ref: <tag>
    rulesets: [general, python]
```

To choose a ruleset's rules or change how they run, give it settings instead:

```yaml
    rulesets:
      python:
        exclude: [no-del-param]
        rules:
          names-match-behavior:
            paths: ["src/**/*.py"]
            severity: warning
```

A git package's `ref` is a tag or commit. Local and CI reviews use the rules at that
`ref`, so a commit gets the same rules everywhere, and a package release changes nothing
until a project moves its `ref`. To try a release, change `ref` locally, or point a
`kind: path` package at a checkout of it.

codeguard fetches each `ref` once into `~/.cache/codeguard/packages` and reuses it, so a
`ref` must not be a branch.

### Upgrade

Pin in CI, auto-update in your dev environment. A commit on `main` reaches no one until
it is released.

**Pin in CI.** A project adopts each codeguard release and each rule package tag in its
own PR, so whatever the upgrade changes in reviews and rule tests shows up there and
nowhere else:

- Move the action's tag (`jig-code/codeguard@v<version>`, and `jig-code/codeguard/test@v<version>`
  if the project defines rules) to the new release.
- Move a rule package's `ref` in `.codeguard/config.yaml` to its new tag.
