# CLI

| Command | Who runs it | What it checks | Calls the model |
|---|---|---|---|
| `codeguard review` | a project using codeguard: the agent's Stop hook, and the action in CI | the project's changed code against the rules it opts into | for judge rules |
| `codeguard test` | whoever writes rules, in a rule package or a project's `.codeguard/` | the rules: pattern rules and gates match their test cases, and judge rules' triggers fire on their eval cases | no |
| `codeguard eval` | whoever writes rules | judge rules: each eval case gets its expected review | yes |

`review` checks code; `test` and `eval` check the rules themselves. [Write a rule
package](#write-a-rule-package) covers `test` and `eval`.

From the project:

```sh
codeguard review              # uncommitted changes
codeguard review --base main  # changes since the merge base with main
codeguard review --all        # every file
codeguard review --dry-run    # pattern rules, then count the judge calls; calls no model
codeguard review --format json  # one JSON object with every diagnostic
codeguard review --judge-errors-as-warnings  # judge calls that couldn't complete don't fail
codeguard review --skip-ci-only  # skip ci_only rules, as the Stop hook does
codeguard test                # pattern rule and gate tests, and judge rule eval triggers
codeguard test --update-all   # the same, regenerating snapshots
codeguard eval                # judge rule evals; calls the configured judge
```
