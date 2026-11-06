# Use codeguard

## Install the plugin

The plugin is codeguard: it ships the CLI and runs it with
[uv](https://docs.astral.sh/uv/getting-started/installation/), so uv is all anyone
working in the project installs. The first review after an install or upgrade takes a
little longer while uv builds codeguard's environment in the plugin's data directory.

Then install the plugin. Project settings enable it but don't install it.

```sh
claude plugin install codeguard@codeguard --scope project
```

Then trust codeguard's hooks in `/hooks`.

## Merge a PR despite a judge error

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

## Keep the plugin up to date

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

## The CLI on its own

[Claude Code](#claude-code) and [Codex](#codex) install the plugin. Codex doesn't give
plugins a command, so writing rules there needs the CLI on its own.

To run codeguard from a terminal, or to write rules in Codex, install the CLI with uv.
It doesn't need the plugin, and the plugin doesn't need it.

```sh
uv tool install git+https://github.com/jig-code/codeguard@v0
```

Upgrade the CLI with `uv tool upgrade codeguard`, if you installed it.

## Troubleshooting

Start
the session in the repository's directory and make changes from there. Claude Code reads a
project's hooks only from the directory a session starts in, and a cloud session over several
repositories starts above them, where no repository's hooks run. 

 When the agent can't fix one, interrupt it
  and fix the rule.

- If the review crashes or uv can't build codeguard's environment, you see why, and the
  stop goes through.
