# Configuration

- Only the listed rulesets run. A ruleset given by name alone runs every rule, at its own
  severity.
- `include` lists the only rules that run, pattern and judged; rules the package adds
  later stay off. `exclude` turns rules off. Set one or the other.
- `rules.<id>` overrides a rule's `paths`, `exclude_paths`, `severity` or `ci_only`.
  `exclude_paths: []` brings back the files its binding leaves out. For the judge model,
  see [a bound rule's judge model](#configuration-reference).
- `severity` on the ruleset sets every rule in it, including rules the package adds
  later; a rule's own `severity` override wins. Only `error` blocks Stop and fails CI,
  so `severity: warning` trials a package: its findings print without blocking. A
  failed judge call takes its rule's severity too.
- `ci_only: true` runs a rule in CI and in a `codeguard review` run by hand, but not in
  the agent's Stop hook. Set it on the ruleset or on one rule; a rule's own `ci_only`
  wins, as with `severity`. It exists for rules too costly to judge every time an agent
  stops, such as a judge rule that reads widely: each Stop hook review spends the
  developer's own Claude subscription, while CI reviews each push to a PR with the
  environment's credentials, on Bedrock or Vertex AI.
  CI still fails the PR on the rule, so the agent meets it there instead of at Stop.
- An unknown ruleset or rule id is an error.
A project runs one ast-grep version for all its rules: codeguard's own, or the version
`.codeguard/config.yaml` sets, which runs through `uv tool run`:

```yaml
ast-grep: 0.45.3
```

codeguard fails when that version is outside a package's `ast-grep` range.

## Configure the judge

A rule's provider and its model resolve separately. Each takes the first of these levels
that names it:

1. The rule's binding (`provider`, `model`): a per-rule override, for a rule whose eval
   passes on one model only.
2. The project's default, `judge` in `.codeguard/config.yaml`, or the
   `CODEGUARD_JUDGE__PROVIDER` and `CODEGUARD_JUDGE__MODEL` variables that override it,
   which is how CI names its judge.
3. The rule package's default, `judge` in `codeguard-package.yaml`.

So a binding that names only a model runs on the provider the project, or CI, sets. With
no provider named, the provider is `claude-cli`, except that a model that isn't a Claude
model with no provider named is a configuration error. With no model named, the `claude-cli`
and `codex-cli` providers run their CLI with no `--model`, so its own default judges; a
`bedrock` or `gemini` run with no model named is an error. `codeguard eval --provider`
and `--model` override the provider or the model for that run ([CLI](cli.md#eval)).
[Judge configuration](architecture.md#judge-configuration) says how a model is named
once, by its vendor's id, and how each provider maps it. The keys:

```yaml
# codeguard-package.yaml: the package's default for its judge rules
judge:
  model: claude-haiku-5-5

# .codeguard/config.yaml: the project's default, and the settings that stay global
judge:
  model: claude-sonnet-5-5          # for rules whose binding names none, over a package's default
  provider: bedrock                 # claude-cli (default), codex-cli, bedrock or gemini
  bedrock:
    inference_prefix: us            # the cross-region inference profile's prefix; default us
  project: my-project               # Vertex AI; default GOOGLE_CLOUD_PROJECT
  location: global                  # default GOOGLE_CLOUD_LOCATION
  calls_at_once: 2                  # Gemini only
```

## Configuration reference

A project's settings live in `.codeguard/config.yaml`, which is committed, so a commit
gets the same review on every machine and in CI. Every setting is optional.

| Setting | Default | What it does | Why the default |
|---|---|---|---|
| `confidence_threshold` | `0.9` | A judged `error` with a lower confidence is reported as a warning, to you rather than the agent, and doesn't block. | Only findings the judge is sure of should stop an agent or fail a PR. A doubtful finding that blocked would send the agent after a violation that may not exist. See [What the hooks check](hooks.md#what-the-hooks-check). |
| `review_time_limit_minutes` | `5` | The review stops judging after this long. Each rule and file it didn't judge gets a `judge_error` diagnostic at the rule's severity, as a failed judge call does. The GitHub Action stops the review 2 minutes after it. | A stuck `claude` call once hung a CI review for 30 minutes with no output. A limit turns a hang into a visible failure. |
| `ast-grep` | the version codeguard installs | The ast-grep version every pattern rule and gate runs with, through `uv tool run`. | One version for every rule, so a rule matches the same code on every machine. codeguard fails when it is outside a package's `ast-grep` range. |
| `packages` | none | The rule packages and rulesets the project uses; see [Rules](#rules). Without it, only the rules in `.codeguard/` run. | A project opts into each ruleset, so no rule runs that the project didn't choose. |
| `packages[].rulesets` | none; required | The rulesets the project runs from the package: a list of names, each running every rule, or a mapping from each name to its settings; see [Rules](#rules). | A project opts into each ruleset by name. |
| `packages[].rulesets.<name>`: `include`, `exclude`, `severity`, `ci_only`, `rules.<id>` | every rule, at its own severity, in every review | Which of a ruleset's rules run, where, and at what severity, in the mapping form; see [Rules](#rules). | |
| `judge.model` | none: the `claude` CLI runs with no `--model`, so its own default judges | The model for judge rules whose binding names none, over a package's default: by its vendor's id, which the provider maps, or by the provider's own id, such as a Bedrock application inference profile's ARN, which it passes through (the profile needs a `ModelId` tag naming the model it routes to); see [Configure the judge](#configure-the-judge). A Bedrock or Vertex AI run needs one named here, in the package or in the binding. | The project decides what judges its code; a package's default covers projects that don't; codeguard has no built-in model of its own. |
| `judge.provider` | `claude-cli` | Where the model runs: `claude-cli` or `bedrock` for Claude, `codex-cli` or `bedrock` for GPT, `gemini` for Gemini. A model that isn't a Claude model needs it set; with none, it is a configuration error. | Which judge runs is configuration, so a switch is one value. CI never uses a subscription: its workflow sets `CODEGUARD_JUDGE__PROVIDER`. |
| `judge.bedrock.inference_prefix` | `us` | The cross-region inference profile prefix Bedrock requests use: `<prefix>.<vendor>.<model>`, `anthropic` or `openai`. | A model is named once, by its vendor's id; where it runs is the environment's. |
| `judge.calls_at_once` | `2` | How many Gemini judge calls run at once; other providers aren't limited by it. | Gemini's pay-as-you-go capacity is shared, so fewer calls keep a review under its tokens-per-minute limit. A `claude` call mostly waits on the network, so it follows the machine. |
| `judge.project`, `judge.location` | `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` | Where Gemini runs; see [Judge with Gemini on Google Cloud](#judge-with-gemini-on-google-cloud). | |

Two things have no setting on purpose:

- **Judge errors fail the review.** A judge call that couldn't complete, including one
  cut off by the time limit, is reported at its rule's severity, so for an `error` rule
  it fails CI. A rule the judge couldn't check is code nobody checked, and a warning in
  a passing check goes unseen: if a setting could turn these into warnings for a
  project, a broken judge, an expired token or a codeguard bug would let every PR
  through. A bypass is always for one PR ([CI](add-codeguard.md#ci)); the Stop hook
  shows judge failures to you instead ([What the hooks check](hooks.md)).
- **A bound rule's judge model.** A rule whose binding names a model is judged with it,
  the one its rule eval passed on alone. A project's `judge.model` applies to every
  other rule, over a package's default ([Configure the judge](#configure-the-judge)).

Settings that decide what a review reports belong in the committed config, so CI and
every machine review a commit the same way. Any setting can be overridden from the
environment by `CODEGUARD_` plus its key, with `__` between the parts of a nested key,
such as `CODEGUARD_JUDGE__PROVIDER` for `judge.provider`; the variable wins over the
file, and an unset variable changes nothing. CI uses this to name its judge, since it has
no subscription. Other variables choose the config file or the codeguard to run, sign
the judge in, or turn on telemetry:

| Variable | Default | What it does |
|---|---|---|
| `CODEGUARD_JUDGE__PROVIDER` | unset: the file's `judge.provider`, else `claude-cli` | Which provider judges: `claude-cli`, `codex-cli`, `bedrock` or `gemini`; CI sets `bedrock` or `gemini`. See [Configure the judge](#configure-the-judge). |
| `CODEGUARD_JUDGE__MODEL` | unset: the file's `judge.model`, else the package's, else none | The model for judge rules whose binding names none; CI sets the one it judges with. |
| `CODEGUARD_CONFIG` | `.codeguard/config.yaml` | The config file to load, relative to the repository root, such as a gitignored `codeguard.local.yaml` for working on a local package. |
| `CODEGUARD` | the codeguard the plugin ships | The codeguard the hooks run instead, such as a checkout's `.venv/bin/codeguard`. |
| `AWS_DEFAULT_REGION`, and the credentials boto3 finds | the AWS CLI's own | How Claude on Bedrock signs in, locally and in CI. |
| `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` | unset | Where Gemini runs, for a `gemini` binding, unless `judge.project` and `judge.location` set it; see [Judge with Gemini on Google Cloud](#judge-with-gemini-on-google-cloud). |
| `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_API_KEY` | Application Default Credentials | How Gemini signs in: a service account key file, or an API key a proxy adds. |
| `LOGFIRE_TOKEN` | none: nothing is sent | Sends a trace of each run to Logfire; see [Telemetry](#telemetry). |
