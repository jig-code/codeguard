# codeguard

Makes coding agents follow your project's coding conventions. Each convention is
written once, in the project, and applies wherever code is written or reviewed: while
Claude Code or Codex works, and in CI.

codeguard adds the checks a project's linters can't do. It doesn't replace or wrap
them.

## Setup

The plugin is codeguard: it ships the CLI and runs it with
[uv](https://docs.astral.sh/uv/getting-started/installation/), so uv is all anyone
working in the project installs. The first review after an install or upgrade takes a
little longer while uv builds codeguard's environment in the plugin's data directory.

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

Then install the plugin. Project settings enable it but don't install it.

```sh
claude plugin install codeguard@codeguard --scope project
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

Then trust codeguard's hooks in `/hooks`.

### CI

```yaml
on: pull_request

jobs:
  codeguard:
    runs-on: ubuntu-latest
    env:
      CODEGUARD_JUDGE__PROVIDER: bedrock
      CODEGUARD_JUDGE__MODEL: claude-haiku-5-5
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

[Run codeguard in CI](docs/add-codeguard.md#ci) explains the action and its judge.

Next, opt into a rule package or write a rule of your own
([Rules](docs/configuration.md#rules)).

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
