# Use codeguard

For everyone working in a repository that has codeguard. Whoever added it committed the
plugin settings and the CI job ([Add codeguard to a project](add-codeguard.md)); this
page is what each engineer does.

## Install the plugin

The plugin ships the codeguard CLI, its review hooks and the writing-rules skill, and
runs the CLI with [uv](https://docs.astral.sh/uv/getting-started/installation/), so uv is
all anyone working in the project installs. The first review after an install or upgrade
takes a little longer while uv builds codeguard's environment.

### Claude Code

Install the plugin ([Discover plugins](https://code.claude.com/docs/en/discover-plugins)):

```sh
claude plugin install codeguard@codeguard --scope project
```

The plugin also puts `codeguard` on the PATH of the commands Claude runs, for skills
such as writing a rule.

### Codex

Trust codeguard's hooks in `/hooks` ([Codex hooks](https://developers.openai.com/codex/hooks)).

## When a review blocks

When the agent stops, codeguard reviews its changes and blocks on an error until it's
fixed. [How a review works](how-a-review-works.md) says what it reviews, what reaches the
agent and what reaches you.

## Merge a PR despite a judge error

A judge call that couldn't complete fails the review, and no setting turns that off
([why](configuration.md#no-setting-on-purpose)). To merge the PR anyway, add the
`codeguard-allow-judge-errors` label to it, so each bypass is chosen for one PR and
shows in its history. The action then passes `--judge-errors-as-warnings` to the review,
so those calls print as warnings, and rule violations still fail. The label doesn't
cover the `eval` input's `codeguard eval`, which still fails on them.

Adding the label starts a new review, and removing it starts a strict one
([the CI job](add-codeguard.md#ci)).

## Keep the plugin up to date

A commit on codeguard's `main` reaches no one until it is released. CI stays on the
release the project pins ([Pin codeguard and rule
packages](add-codeguard.md#pin-codeguard-and-rule-packages)).

Turn on auto-update for the codeguard marketplace in your dev environment, so you meet a
release's changes before CI does ([Discover
plugins](https://code.claude.com/docs/en/discover-plugins)). If a release breaks a branch
you're working on, turn auto-update off until the fix ships. To update by hand:

```sh
claude plugin marketplace update codeguard
claude plugin update codeguard@codeguard --scope project
```

## The CLI on its own

The plugin runs codeguard for the agent. To run codeguard from a terminal, or to write
rules in Codex, install the CLI with uv. It doesn't need the plugin, and the plugin
doesn't need it.

```sh
uv tool install git+https://github.com/jig-code/codeguard@v0
```

Upgrade the CLI with `uv tool upgrade codeguard`, if you installed it. [CLI](cli.md)
lists its commands.

## Troubleshooting

- **No review runs when the agent stops.** Start the session in the repository's
  directory and make changes from there, so Claude Code loads the project's hooks
  ([Hooks](https://code.claude.com/docs/en/hooks)).
- **The agent can't fix an error.** It blocks every time the agent stops until the error
  is fixed, so interrupt the agent and fix the rule.
- **The review crashed, or uv couldn't build codeguard's environment.** You see why, and
  the stop goes through.
