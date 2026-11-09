# CLI

| Command | Who runs it | What it checks | Calls the model |
|---|---|---|---|
| `codeguard review` | a project using codeguard: the agent's Stop hook, and the action in CI | the project's changed code against the rules it opts into | for judge rules |
| `codeguard test` | whoever writes rules, in a rule package or a project's `.codeguard/` | the rules: pattern rules and gates match their test cases, and judge rules' triggers fire on their eval cases | no |
| `codeguard eval` | whoever writes rules | judge rules: each eval case gets its expected review | yes |

`review` checks code; `test` and `eval` check the rules themselves.
[Write rules](write-rules.md#test-a-judge-rule) covers `test` and `eval`.

Every command takes `-h` for its help.

## review

From the project:

```sh
codeguard review              # uncommitted changes
codeguard review --base main  # changes since the merge base with main
codeguard review --all        # every file
codeguard review --dry-run    # pattern rules, then list the judge calls; calls no model
codeguard review --format json  # one JSON object with every diagnostic
codeguard review --judge-errors-as-warnings  # judge calls that couldn't complete don't fail
codeguard review --skip-ci-only  # skip ci_only rules, as the Stop hook does
codeguard review --host codex   # name the caller in telemetry; changes nothing else
```

## test

```sh
codeguard test                # pattern rule and gate tests, and judge rule eval triggers
codeguard test --update-all   # the same, regenerating snapshots
codeguard test --missing-why fail  # a rule without a why fails; warn (default) or off
codeguard test path/to/package  # test a package outside the current repository
```

## eval

```sh
codeguard eval                # judge rule evals, each case once with its binding's model
codeguard eval --repeat 2     # judge each case twice; default 1
codeguard eval path/to/package  # evaluate a package outside the current repository
```

Options to judge part of a package, or with another model:

- `--rule <id>` evaluates only that judge rule; repeat it for more. The check for an
  eval with an `invalid` case covers only the rules selected.
- `--case <text>` judges only the cases whose name contains the text; repeat it to
  judge the cases matching any of them. A rule with no matching case is left out.
- `--provider claude-cli`, `--provider codex-cli`, `--provider gemini` or
  `--provider bedrock` judges every selected rule with that provider instead of its
  binding's. `--model` names the model; it defaults to `claude-sonnet-5-5` for
  `claude-cli`, `gpt-6-luna` for `codex-cli`, `gemini-3.1-pro-preview` for `gemini` and
  `us.anthropic.claude-haiku-5-5` for `bedrock`.

A `--rule` that names no judge rule, or a `--case` that no selected rule's case name
contains, fails the eval before any case is judged.

```sh
codeguard eval --rule mock-only-at-boundary --case "a patch"
codeguard eval --rule mock-only-at-boundary --case "a patch" --repeat 2
codeguard eval --provider gemini
codeguard eval --provider gemini --repeat 2
```

## config

```sh
codeguard config review_time_limit_minutes  # print a setting, or its default
```
