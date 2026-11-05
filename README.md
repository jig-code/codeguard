# codeguard

Makes coding agents follow your project's coding conventions. Each convention is
written once, in the project, and applies wherever code is written or reviewed: while
Claude Code or Codex works, and in CI.

codeguard adds the checks a project's linters can't do. It doesn't replace or wrap
them.

## Documentation

For a project that uses codeguard:

- [Run codeguard in CI and keep it current](docs/add-codeguard.md): CI, formatters, the
  CLI on its own, and upgrades.
- [What the hooks check](docs/hooks.md): what a review sends the judge and what it
  reports.
- [Configuration](docs/configuration.md): rule packages, the judge, telemetry, and every
  setting.
- [CLI](docs/cli.md): the commands and their options.

For whoever writes rules:

- [Write a rule package](docs/rule-packages.md): the files a rule is made of, and how to
  test them. The plugin's [writing-rules skill](skills/writing-rules/SKILL.md) says how
  to write a rule.

For whoever works on codeguard:

- [Contributing](docs/CONTRIBUTING.md): working on codeguard, and releases.
- [Architecture](docs/architecture.md): how codeguard works and the invariants every
  change keeps.
- [Testing](docs/testing.md): which checks a change needs.
