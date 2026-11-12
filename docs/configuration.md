# Configuration reference

A project's settings live in `.codeguard/config.yaml`, which is committed, so a commit
gets the same review on every machine and in CI. Every setting is optional. The GitHub
Action's inputs are in [`action.yml`](../action.yml).
[Add codeguard to a project](add-codeguard.md) and [Choose a judge](judges.md) show them
in use.

## Settings

| Setting | Default | What it does | Why the default |
|---|---|---|---|
| `confidence_threshold` | `0.9` | A judged `error` with a lower confidence is reported as a warning, to you rather than the agent, and doesn't block. | Only findings the judge is sure of should stop an agent or fail a PR. A doubtful finding that blocked would send the agent after a violation that may not exist. See [How a review works](how-a-review-works.md). |
| `review_time_limit_minutes` | `5` | The review stops judging after this long. Each rule and file it didn't judge is reported as not checked, at the rule's severity. The GitHub Action stops the review 2 minutes after it. | A stuck `claude` call once hung a CI review for 30 minutes with no output. A limit turns a hang into a visible failure. |
| `ast-grep` | the version codeguard installs | The ast-grep version every pattern rule and gate runs with, through `uv tool run`, such as `0.45.3`. | One version for every rule, so a rule matches the same code on every machine. codeguard fails when it is outside a package's `ast-grep` range. |
| `packages` | none | The rule packages and rulesets the project uses; see [Opt into a rule package](add-codeguard.md#opt-into-a-rule-package). Without it, only the rules in `.codeguard/` run. | A project opts into each ruleset, so no rule runs that the project didn't choose. |
| `packages[].rulesets` | none; required | The rulesets the project runs from the package: a list of names, each running every rule, or a mapping from each name to its settings; see [Rule package keys](#rule-package-keys). | A project opts into each ruleset by name. |
| `packages[].rulesets.<name>.include` | every rule in the ruleset | The only rules that run. Rules the package adds later stay off. Set it or `exclude`, not both. | |
| `packages[].rulesets.<name>.exclude` | none | Rules that don't run. | |
| `packages[].rulesets.<name>.severity` | each rule's own | The severity of every rule in the ruleset, including rules the package adds later. A rule's own override wins. | `warning` trials a ruleset: its findings print without blocking. |
| `packages[].rulesets.<name>.ci_only` | `false` | Runs every rule in the ruleset only in CI and in reviews run by hand, not in the agent's Stop hook. A rule's own override wins. | A hook review spends the developer's subscription each time an agent stops; `true` keeps a costly rule to CI. See [Rule package keys](#rule-package-keys). |
| `packages[].rulesets.<name>.rules.<id>` | the binding's | Overrides a rule's `paths`, `exclude_paths`, `severity` or `ci_only`. | |
| `judge.provider`, `judge.model` | `claude-cli` and the `claude` CLI's own default model | The judge provider and model for each judge rule whose binding leaves them out; see [Choose a judge](judges.md). | A project whose developers and CI judge with another provider names it once, instead of in every binding. |
| `judge.calls_at_once` | `2` | How many Gemini judge calls run at once; other providers aren't limited by it. | Gemini's pay-as-you-go capacity is shared, so fewer calls keep a review under its tokens-per-minute limit. |

## Rule package keys

A package entry's `rulesets` lists the rulesets to run, or maps each to its settings
([Opt into a rule package](add-codeguard.md#opt-into-a-rule-package)):

- Only the listed rulesets run. A ruleset given by name alone runs every rule, at its own
  severity.
- `include` lists the only rules that run, pattern and judged; rules the package adds
  later stay off. `exclude` turns rules off. Set one or the other.
- `rules.<id>` overrides a rule's `paths`, `exclude_paths`, `severity` or `ci_only`.
  `exclude_paths: []` brings back the files its binding leaves out. For the judge model,
  see [No setting on purpose](#no-setting-on-purpose).
- `severity` on the ruleset sets every rule in it, including rules the package adds
  later; a rule's own `severity` override wins. Only `error` blocks Stop and fails CI,
  so `severity: warning` trials a package: its findings print without blocking. A
  failed judge call takes its rule's severity too.
- `ci_only: true` runs a rule in CI and in a `codeguard review` run by hand, but not in
  the agent's Stop hook. Set it on the ruleset or on one rule; a rule's own `ci_only`
  wins, as with `severity`. It exists for rules too costly to judge every time an agent
  stops, such as a judge rule that reads widely: each Stop hook review spends the
  developer's own Claude subscription, while CI reviews each push to a PR with the
  project's token. CI still fails the PR on the rule, so the agent meets it there
  instead of at Stop.
- An unknown ruleset or rule id is an error.

Diagnostics name a packaged rule by package, ruleset and id:
`codeguard/python/no-del-param`.

## Environment variables

Settings that decide what a review reports belong in the committed config, not in the
environment, so CI and every machine review a commit the same way. Environment variables
only choose the config file or the codeguard to run, choose and sign in the judge, or turn
on telemetry:

| Variable | Default | What it does |
|---|---|---|
| `CODEGUARD_CONFIG` | `.codeguard/config.yaml` | The config file to load, relative to the repository root, such as a gitignored `codeguard.local.yaml` for working on a local package. |
| `CODEGUARD` | the codeguard the plugin ships | The codeguard the hooks run instead, such as a checkout's `.venv/bin/codeguard`. |
| `CODEGUARD_JUDGE__PROVIDER`, `CODEGUARD_JUDGE__MODEL` | unset | Set `judge.provider` and `judge.model` in place of the config file's, such as for a CI job that judges with Bedrock while developers use the `claude` CLI. An empty variable counts as unset. |
| `CLAUDE_CODE_OAUTH_TOKEN` | the `claude` CLI's own sign-in | The subscription token the judge runs with, in CI. |
| `AWS_DEFAULT_REGION`, and the credentials boto3 finds | the AWS CLI's own | Where Bedrock runs and how it signs in; see [Bedrock](judges.md#bedrock). |
| `CODEGUARD_JUDGE__GEMINI__PROJECT` | unset; Gemini judge calls fail without it | The Google Cloud project Gemini runs in; see [Gemini on Google Cloud](judges.md#gemini-on-google-cloud). |
| `CODEGUARD_JUDGE__GEMINI__LOCATION` | `global` | The Vertex AI location Gemini runs in. |
| `CODEGUARD_JUDGE__GEMINI__CREDENTIALS_FILE`, `CODEGUARD_JUDGE__GEMINI__API_KEY` | unset; Gemini judge calls fail without one | How Gemini signs in: a service account key file, or an API key. Set one, not both. These Gemini settings come from the environment only: `judge.gemini` in the config file is an error. |
| `LOGFIRE_TOKEN` | none: nothing is sent | Sends a trace of each run to Logfire; see [Telemetry](telemetry.md). |

## No setting on purpose

- **Judge errors fail the review.** A judge call that couldn't complete, including one
  cut off by the time limit, is reported at its rule's severity, so for an `error` rule
  it fails CI. A rule the judge couldn't check is code nobody checked, and a warning in
  a passing check goes unseen: if a setting could turn these into warnings for a
  project, a broken judge, an expired token or a codeguard bug would let every PR
  through. A bypass is for one PR at a time
  ([Merge a PR despite a judge error](using-codeguard.md#merge-a-pr-despite-a-judge-error)),
  and shows in the PR's history. The Stop hook passes `--judge-errors-as-warnings`,
  because the agent can't fix a judge failure. It shows the failure to you, and CI still
  fails on it.
- **A rule's judge model.** A judge rule is judged with the provider and model its binding
  names, the ones its rule eval passed on. A project can't switch it to a model the eval
  never ran on: `judge.provider` and `judge.model` apply only to bindings that leave them
  out.
