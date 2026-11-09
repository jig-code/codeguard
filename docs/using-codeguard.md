# Use codeguard

## Install the plugin

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

Upgrade the CLI with `uv tool upgrade codeguard`, if you installed it.
