# Use codeguard

For everyone working in a repository that has codeguard. Whoever added it committed the
plugin settings and the CI job ([Add codeguard to a project](add-codeguard.md)); this
page is what each engineer does.

## Install the plugin

The plugin is codeguard: it ships the CLI and runs it with
[uv](https://docs.astral.sh/uv/getting-started/installation/), so uv is all anyone
working in the project installs. The first review after an install or upgrade takes a
little longer while uv builds codeguard's environment in the plugin's data directory.

### Claude Code

Install the plugin. The project's settings enable it but don't install it.

```sh
claude plugin install codeguard@codeguard --scope project
```

### Codex

Trust codeguard's hooks in `/hooks`.

## When a review blocks

When the agent stops, codeguard reviews its changes and blocks on an error until it's
fixed. [How a review works](how-a-review-works.md) says what it reviews, what reaches the
agent and what reaches you.

## Merge a PR despite a judge error

A judge call that couldn't complete fails the review, and no setting turns that off
([why](configuration.md#no-setting-on-purpose)). To merge the PR anyway, add the
`codeguard-allow-judge-errors` label to it, so each bypass is chosen for one PR and
shows in its history. The action then passes
`--judge-errors-as-warnings` to the review, so those calls print as warnings, and rule
violations still fail. The label doesn't cover the `eval` input's `codeguard eval`,
which still fails on them.

Re-running the job doesn't pick up the label: a re-run reuses the event that started
the workflow, with the PR's labels at that time. Adding the label starts a new review,
and removing it starts a strict one, when the workflow triggers on `labeled` and
`unlabeled` for that label, as [the CI job](add-codeguard.md#ci) does.

## Keep the plugin up to date

A commit on codeguard's `main` reaches no one until it is released. CI stays on the
release the project pins ([Pin codeguard and rule
packages](add-codeguard.md#pin-codeguard-and-rule-packages)).

Auto-update the plugin in your dev environment, so you meet a release's changes before
CI does: in `/plugin`, turn on auto-update for the codeguard marketplace (Marketplaces,
then codeguard). Auto-update is off by default for marketplaces outside Anthropic's own. It
applies new releases in the background, and they take effect in the next session. If a
release breaks a branch you're working on, turn auto-update off until the fix ships. To
update by hand, run these, then `/reload-plugins` or start a new session:

```sh
claude plugin marketplace update codeguard
claude plugin update codeguard@codeguard --scope project
```

## The CLI on its own

The plugin runs codeguard for the agent. Codex doesn't give plugins a command, so
writing rules there needs the CLI on its own.

To run codeguard from a terminal, or to write rules in Codex, install the CLI with uv.
It doesn't need the plugin, and the plugin doesn't need it.

```sh
uv tool install git+https://github.com/jig-code/codeguard@v0
```

Upgrade the CLI with `uv tool upgrade codeguard`, if you installed it. [CLI](cli.md)
lists its commands.

## Troubleshooting

- **No review runs when the agent stops.** Start the session in the repository's
  directory and make changes from there. Claude Code reads a project's hooks only from
  the directory a session starts in, and a cloud session over several repositories
  starts above them, where no repository's hooks run.
- **The agent can't fix an error.** It blocks every time the agent stops until the error
  is fixed, so interrupt the agent and fix the rule.
- **The review crashed, or uv couldn't build codeguard's environment.** You see why, and
  the stop goes through.
