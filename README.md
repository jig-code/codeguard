# codeguard

Makes coding agents follow your project's coding conventions. Each convention is
written once, in the project, and applies wherever code is written or reviewed: while
Claude Code or Codex works, and in CI.

codeguard adds the checks a project's linters can't do. It doesn't replace or wrap
them.

## Setup

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/); the plugin runs
   codeguard with it.
2. Add the plugin for Claude Code or Codex, and the GitHub Action for CI, as
   [Add codeguard to a project](docs/add-codeguard.md) shows.
3. Opt into a rule package's rulesets in `.codeguard/config.yaml`, or write a rule of your
   own:

   ```yaml
   packages:
     - kind: git
       git: https://github.com/betterwithranch/codeguard-rules.git
       ref: v0.6.0
       rulesets: [general, python]
   ```

When the agent stops, codeguard reviews its changes and blocks on an error until it's
fixed ([How a review works](docs/how-a-review-works.md)).

## Documentation

For a project that uses codeguard:

- [Add codeguard to a project](docs/add-codeguard.md): Claude Code, Codex, CI, rule
  packages, formatters, the CLI on its own, and upgrades.
- [How a review works](docs/how-a-review-works.md): what a review sends the judge, what it
  reports, and the hooks.
- [Choose a judge](docs/judges.md): the providers, and setting up Codex, Gemini and
  Bedrock.
- [Configuration reference](docs/configuration.md): every setting and environment
  variable, and which source wins.
- [Telemetry](docs/telemetry.md): the traces codeguard sends to Logfire.
- [CLI](docs/cli.md): the commands and their options.

For whoever writes rules:

- [Write a rule package](docs/rule-packages.md): the files a rule is made of, and how to
  test them. The plugin's [writing-rules skill](skills/writing-rules/SKILL.md) says how
  to write a rule.

For whoever works on codeguard:

- [Contributing](docs/CONTRIBUTING.md): working on codeguard, and releases.
- [Architecture](docs/architecture.md): an overview of how codeguard works and the
  invariants every change keeps, with [the review pipeline](docs/review-pipeline.md) and
  [the judge](docs/judge-design.md) in detail.
- [Testing](docs/testing.md): which checks a change needs.
