# Run codeguard in CI and keep it current

## CI

The README's [CI example](../README.md#ci) adds the action. It reviews the files changed
since the merge base with the PR's base branch, then runs the rule tests. The job's
`CODEGUARD_JUDGE__PROVIDER` and `CODEGUARD_JUDGE__MODEL` name its judge: Claude on
Amazon Bedrock with the job's AWS credentials, as in the example, or Gemini on Vertex AI
with `google-github-actions/auth` ([Judge with Gemini on Google
Cloud](configuration.md#judge-with-gemini-on-google-cloud)). [Configure the
judge](configuration.md#configure-the-judge) says how those variables and the project's
config combine.

A judge call that couldn't complete fails the review, and no setting turns that off
([why](configuration.md#configuration-reference)). To merge the PR anyway, add the
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

The README's [Setup](../README.md#setup) installs the plugin. In Claude Code, the plugin
also puts `codeguard` on the PATH of the commands Claude runs, for skills such as
writing a rule. Codex doesn't give plugins a command, so writing rules there needs the
CLI on its own.

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
