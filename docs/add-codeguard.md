# Add codeguard to a project

The one-time setup for a repository: the plugin settings, the CI job and its judge, the
rule packages, and the formatters. Each engineer then installs the plugin
([Use codeguard](using-codeguard.md)).

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

## CI

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened, labeled, unlabeled]

jobs:
  codeguard:
    if: >-
      (github.event.action != 'labeled' && github.event.action != 'unlabeled')
      || github.event.label.name == 'codeguard-allow-judge-errors'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
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
then runs the rule tests. [GitHub Action inputs](configuration.md#github-action-inputs)
lists what else it takes.

The `labeled` and `unlabeled` types re-run the review when an engineer adds or removes
the `codeguard-allow-judge-errors` label, which lets one PR merge despite a judge call
that couldn't complete ([Merge a PR despite a judge
error](using-codeguard.md#merge-a-pr-despite-a-judge-error)). The `if` keeps other
labels from re-running the review and its judge calls.

### Choose the CI judge

CI has no subscription, so the job's `CODEGUARD_JUDGE__PROVIDER` and
`CODEGUARD_JUDGE__MODEL` name its judge: Claude on Amazon Bedrock with the job's AWS
credentials, as in the example, or Gemini on Vertex AI with `google-github-actions/auth`.
[Choose a judge](judges.md) says how to set up each provider and grant the job access,
and [Which judge runs](configuration.md#which-judge-runs) how those variables and the
project's config combine.

## Opt into a rule package

A project's own rules live under `.codeguard/` ([Write rules](write-rules.md)). The two
kinds of rule are in [Rules](architecture.md#rules).

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

A git package's `ref` is a tag or commit. codeguard fetches each `ref` once into
`~/.cache/codeguard/packages` and reuses it, so a `ref` must not be a branch. A private
package needs a token in CI ([A private package](write-rules.md#a-private-package)).

## Pin codeguard and rule packages

Local and CI reviews use the rules at a package's `ref`, so a commit gets the same rules
everywhere, and a package release changes nothing until the project moves its `ref`.
Pin the action to a release tag, as above, for the same reason.

Adopt each codeguard release and each rule package tag in its own PR, so whatever the
upgrade changes in reviews and rule tests shows up there and nowhere else:

- Move the action's tag (`jig-code/codeguard@v<version>`) to the new release.
- Move a rule package's `ref` in `.codeguard/config.yaml` to its new tag.

To try a package release first, change `ref` locally, or point a `kind: path` package at
a checkout of it ([Try a local package](write-rules.md#try-a-local-package)).

## Run formatters first

Format code before codeguard reviews it. A formatter that runs after the review changes
code that was never reviewed, and it changes the file, so the next review can't reuse
the cached verdict: it calls the model again and can reach a different verdict.

- In Claude Code, format each file when it's edited, in a `PostToolUse` hook on `Edit`
  and `Write`, not in a `Stop` hook, where it can run after codeguard's review
  ([Hooks](https://code.claude.com/docs/en/hooks)).
- In CI, run the format check before the codeguard step.
- Format an unformatted codebase in a commit of its own. Reformatted lines are changed
  lines, so formatting inside a feature change sends every one of them to the judge.

## Tell your team

Each engineer installs the plugin, and Codex users trust its hooks, as
[Use codeguard](using-codeguard.md) shows. Point them there.
