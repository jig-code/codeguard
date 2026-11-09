# Configuration reference

## Rule package keys

- Only the listed rulesets run. A ruleset given by name alone runs every rule, at its own
  severity.
- `include` lists the only rules that run, pattern and judged; rules the package adds
  later stay off. `exclude` turns rules off. Set one or the other.
- `rules.<id>` overrides a rule's `paths`, `exclude_paths`, `severity` or `ci_only`.
  `exclude_paths: []` brings back the files its binding leaves out. A judge rule's
  model can't be overridden: its evals pass on the model its binding names.
- `severity` on the ruleset sets every rule in it, including rules the package adds
  later; a rule's own `severity` override wins. Only `error` blocks Stop and fails CI,
  so `severity: warning` trials a package: its findings print without blocking. A
  failed judge call takes its rule's severity too.
- `ci_only: true` runs a rule in CI and in a `codeguard review` run by hand, but not in
  the agent's Stop hook. Set it on the ruleset or on one rule; a rule's own `ci_only`
  wins, as with `severity`. It exists for rules too costly to judge every time an agent
  stops, such as a judge rule that reads widely: each Stop hook review spends the
  developer's own Claude subscription, while CI reviews each push to a PR with the
  project's token.
  CI still fails the PR on the rule, so the agent meets it there instead of at Stop.
- An unknown ruleset or rule id is an error.

Diagnostics name a packaged rule by package, ruleset and id:
`betterwithranch/python/no-del-param`.

A project runs one ast-grep version for all its rules: codeguard's own, or the version
`.codeguard/config.yaml` sets, which runs through `uv tool run`:

```yaml
ast-grep: 0.45.3
```

codeguard fails when that version is outside a package's `ast-grep` range.

## Configuration reference

A project's settings live in `.codeguard/config.yaml`, which is committed, so a commit
gets the same review on every machine and in CI. Every setting is optional.

| Setting | Default | What it does | Why the default |
|---|---|---|---|
| `confidence_threshold` | `0.9` | A judged `error` with a lower confidence is reported as a warning, to you rather than the agent, and doesn't block. | Only findings the judge is sure of should stop an agent or fail a PR. A doubtful finding that blocked would send the agent after a violation that may not exist. See [What the hooks check](#what-the-hooks-check). |
| `review_time_limit_minutes` | `5` | The review stops judging after this long. Each rule and file it didn't judge is reported as not checked, at the rule's severity. The GitHub Action stops the review 2 minutes after it. | A stuck `claude` call once hung a CI review for 30 minutes with no output. A limit turns a hang into a visible failure. |
| `ast-grep` | the version codeguard installs | The ast-grep version every pattern rule and gate runs with, through `uv tool run`. | One version for every rule, so a rule matches the same code on every machine. codeguard fails when it is outside a package's `ast-grep` range. |
| `packages` | none | The rule packages and rulesets the project uses; see [Rules](#rules). Without it, only the rules in `.codeguard/` run. | A project opts into each ruleset, so no rule runs that the project didn't choose. |
| `packages[].rulesets` | none; required | The rulesets the project runs from the package: a list of names, each running every rule, or a mapping from each name to its settings; see [Rules](#rules). | A project opts into each ruleset by name. |
| `packages[].rulesets.<name>.include` | every rule in the ruleset | The only rules that run. Rules the package adds later stay off. Set it or `exclude`, not both. | |
| `packages[].rulesets.<name>.exclude` | none | Rules that don't run. | |
| `packages[].rulesets.<name>.severity` | each rule's own | The severity of every rule in the ruleset, including rules the package adds later. A rule's own override wins. | `warning` trials a ruleset: its findings print without blocking. |
| `packages[].rulesets.<name>.ci_only` | `false` | Runs every rule in the ruleset only in CI and in reviews run by hand, not in the agent's Stop hook. A rule's own override wins. | A hook review spends the developer's subscription each time an agent stops; `true` keeps a costly rule to CI. See [Rules](#rules). |
| `packages[].rulesets.<name>.rules.<id>` | the binding's | Overrides a rule's `paths`, `exclude_paths`, `severity` or `ci_only`. | |
| `judge.calls_at_once` | `2` | How many Gemini judge calls run at once; other providers aren't limited by it. | Gemini's pay-as-you-go capacity is shared, so fewer calls keep a review under its tokens-per-minute limit. |
| `judge.project`, `judge.location` | `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` | Where Gemini runs; see [Judge with Gemini on Google Cloud](#judge-with-gemini-on-google-cloud). | |

Two things have no setting on purpose:

- **Judge errors fail the review.** A judge call that couldn't complete, including one
  cut off by the time limit, is reported at its rule's severity, so for an `error` rule
  it fails CI. A rule the judge couldn't check is code nobody checked, and a warning in
  a passing check goes unseen: if a setting could turn these into warnings for a
  project, a broken judge, an expired token or a codeguard bug would let every PR
  through. A bypass is always for one PR: the `codeguard-allow-judge-errors` label
  ([CI](#ci)), which shows in the PR's history. The Stop hook always passes
  `--judge-errors-as-warnings`, because the agent can't fix a judge failure. It shows
  the failure to you, and CI still fails on it.
- **A rule's judge model.** A judge rule is judged with the model its binding names, the
  one its rule eval passed on. A project can't switch it to a model the eval never ran
  on.

Settings that decide what a review reports belong in the committed config, not in the
environment, so CI and every machine review a commit the same way. Environment variables
only choose the config file or the codeguard to run, sign the judge in, or turn on
telemetry:

| Variable | Default | What it does |
|---|---|---|
| `CODEGUARD_CONFIG` | `.codeguard/config.yaml` | The config file to load, relative to the repository root, such as a gitignored `codeguard.local.yaml` for working on a local package. |
| `CODEGUARD` | the codeguard the plugin ships | The codeguard the hooks run instead, such as a checkout's `.venv/bin/codeguard`. |
| `CLAUDE_CODE_OAUTH_TOKEN` | the `claude` CLI's own sign-in | The subscription token the judge runs with, in CI. |
| `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` | unset | Where Gemini runs, for a `gemini` binding, unless `judge.project` and `judge.location` set it; see [Judge with Gemini on Google Cloud](#judge-with-gemini-on-google-cloud). |
| `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_API_KEY` | Application Default Credentials | How Gemini signs in: a service account key file, or an API key a proxy adds. |
| `LOGFIRE_TOKEN` | none: nothing is sent | Sends a trace of each run to Logfire; see [Telemetry](#telemetry). |
