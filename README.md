# codeguard

Makes coding agents follow your project's coding conventions. Each convention is
written once, in the project, and applies wherever code is written or reviewed: while
Claude Code or Codex works, and in CI.

codeguard adds the checks a project's linters can't do. It doesn't replace or wrap
them. A pattern rule matches code by its syntax tree, as a linter does; a judge rule
states a convention in prose, and a model judges each change against it. When the agent
stops, codeguard reviews its changes and blocks on an error until it's fixed.

Judge rules call a model: at the agent's Stop on the developer's own subscription, and
in CI with the project's Claude token or cloud account ([Choose a judge](docs/judges.md)).
[Telemetry](docs/telemetry.md) records each judge call's tokens and cost.

## Setup

1. Commit the plugin settings and add the CI job, as
   [Add codeguard to a project](docs/add-codeguard.md) shows.
2. Opt into a rule package's rulesets, or write rules of your own
   ([Write and test rules](#write-and-test-rules)).
3. Each engineer installs [uv](https://docs.astral.sh/uv/getting-started/installation/)
   and the plugin ([Use codeguard](docs/using-codeguard.md)).

## Write and test rules

Ask the agent for the rule. The plugin's
[writing-rules skill](skills/writing-rules/SKILL.md) writes it, in the project's
`.codeguard/` or a ruleset of a [rule package](docs/rule-packages.md).

Then test it with the CLI ([The CLI on its own](docs/using-codeguard.md#the-cli-on-its-own)),
in the project's root, or in a package's root for every ruleset:

1. `codeguard test` checks pattern rules and gates against their tests, and judge rules'
   triggers on their eval cases. It calls no model. A pattern rule needs only this.
2. For a judge rule, `codeguard eval` reviews each eval case once with the binding's
   model, to verify the change.
3. Once it passes, `codeguard eval --repeat 2` reviews each case twice more. A case passes
   when it gets its expected review on all 3 runs.

## Documentation

For a project that uses codeguard:

- [Add codeguard to a project](docs/add-codeguard.md): when you add codeguard to a
  repository, once: the plugin settings, the CI job, rule packages and formatters.
- [Use codeguard](docs/using-codeguard.md): for every engineer on the repository:
  installing and updating the plugin, merging past a judge error, and troubleshooting.
- [Choose a judge](docs/judges.md): when you set up a provider: Codex, Gemini on Vertex
  AI, or Bedrock.
- [How a review works](docs/how-a-review-works.md): when you want to know what a review
  sends the judge, what it reports, and what the hooks do.
- [Configuration reference](docs/configuration.md): when you look up a setting, an
  environment variable or a GitHub Action input.
- [CLI](docs/cli.md): when you look up a command or option.
- [Telemetry](docs/telemetry.md): when you want traces of codeguard's runs in Logfire.

For whoever writes rules or maintains a rule package:

- [Make a rule package](docs/rule-packages.md): when you start or maintain a package: its
  repo and manifest, CI and releases, and trying a local or private one.
- [Rule formats](docs/rule-formats.md): when you look up the format of a binding, a gate,
  a trigger or a rule eval. The plugin's [writing-rules
  skill](skills/writing-rules/SKILL.md) says how to write a rule.

For whoever works on codeguard:

- [Contributing](docs/CONTRIBUTING.md): working on codeguard, and releases.
- [Architecture](docs/architecture.md): why codeguard works as it does, and the
  invariants every change keeps.
- [Testing](docs/testing.md): which of codeguard's tests a change needs you to run.

## Help and maintainers

Report a bug or ask a question in
[GitHub issues](https://github.com/jig-code/codeguard/issues). codeguard is maintained by
Craig Israel.
