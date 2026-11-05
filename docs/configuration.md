# Configuration reference

A project's settings live in `.codeguard/config.yaml`, which is committed, so a commit
gets the same review on every machine and in CI. Every setting is optional.
[Add codeguard to a project](add-codeguard.md) and [Choose a judge](judges.md) show them
in use.

## Settings

| Setting | Default | What it does | Why the default |
|---|---|---|---|
| `confidence_threshold` | `0.9` | A judged `error` with a lower confidence is reported as a warning, to you rather than the agent, and doesn't block. | Only findings the judge is sure of should stop an agent or fail a PR. A doubtful finding that blocked would send the agent after a violation that may not exist. See [How a review works](how-a-review-works.md). |
| `review_time_limit_minutes` | `5` | The review stops judging after this long. Each rule and file it didn't judge gets a `judge_error` diagnostic at the rule's severity, as a failed judge call does. The GitHub Action stops the review 2 minutes after it. | A stuck `claude` call once hung a CI review for 30 minutes with no output. A limit turns a hang into a visible failure. |
| `ast-grep` | the version codeguard installs | The ast-grep version every pattern rule and gate runs with, through `uv tool run`. | One version for every rule, so a rule matches the same code on every machine. codeguard fails when it is outside a package's `ast-grep` range. |
| `packages` | none | The rule packages and rulesets the project uses; see [Opt into a rule package](add-codeguard.md#opt-into-a-rule-package). Without it, only the rules in `.codeguard/` run. | A project opts into each ruleset, so no rule runs that the project didn't choose. |
| `packages[].rulesets` | none; required | The rulesets the project runs from the package: a list of names, each running every rule, or a mapping from each name to its settings; see [Rule package keys](#rule-package-keys). | A project opts into each ruleset by name. |
| `packages[].rulesets.<name>`: `include`, `exclude`, `severity`, `ci_only`, `rules.<id>` | every rule, at its own severity, in every review | Which of a ruleset's rules run, where, and at what severity, in the mapping form; see [Rule package keys](#rule-package-keys). | |
| `judge.model` | none: the `claude` CLI runs with no `--model`, so its own default judges | The model for judge rules whose binding names none, over a package's default: by its vendor's id, which the provider maps, or by the provider's own id, such as a Bedrock application inference profile's ARN, which it passes through (the profile needs a `ModelId` tag naming the model it routes to); see [Which judge runs](#which-judge-runs). A Bedrock or Vertex AI run needs one named here, in the package or in the binding. | The project decides what judges its code; a package's default covers projects that don't; codeguard has no built-in model of its own. |
| `judge.provider` | `claude-cli` | Where the model runs: `claude-cli` or `bedrock` for Claude, `codex-cli` or `bedrock` for GPT, `gemini` for Gemini. A model that isn't a Claude model needs it set; with none, it is a configuration error. | Which judge runs is configuration, so a switch is one value. CI never uses a subscription: its workflow sets `CODEGUARD_JUDGE__PROVIDER`. |
| `judge.bedrock.inference_prefix` | `us` | The cross-region inference profile prefix Bedrock requests use: `<prefix>.<vendor>.<model>`, `anthropic` or `openai`. | A model is named once, by its vendor's id; where it runs is the environment's. |
| `judge.calls_at_once` | `2` | How many Gemini judge calls run at once; other providers aren't limited by it. | Gemini's pay-as-you-go capacity is shared, so fewer calls keep a review under its tokens-per-minute limit. A `claude` call mostly waits on the network, so it follows the machine. |
| `judge.project`, `judge.location` | `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` | Where Gemini runs; see [Gemini on Google Cloud](judges.md#gemini-on-google-cloud). | |

## Rule package keys

A package entry's `rulesets` lists the rulesets to run, or maps each to its settings
([Opt into a rule package](add-codeguard.md#opt-into-a-rule-package)):

- Only the listed rulesets run. A ruleset given by name alone runs every rule, at its own
  severity.
- `include` lists the only rules that run, pattern and judged; rules the package adds
  later stay off. `exclude` turns rules off. Set one or the other.
- `rules.<id>` overrides a rule's `paths`, `exclude_paths`, `severity` or `ci_only`.
  `exclude_paths: []` brings back the files its binding leaves out. For the judge model,
  see [no setting on purpose](#no-setting-on-purpose).
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

## Which judge runs

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
[How a model is named](judge-design.md#how-a-model-is-named) says how each provider maps
a model's id, and [Choose a judge](judges.md) how to set one up. The keys:

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

## Which source wins

Settings that decide what a review reports belong in the committed config, so CI and
every machine review a commit the same way. A setting comes from the first of these that
sets it:

1. An environment variable named `CODEGUARD_` plus its key, with `__` between the parts
   of a nested key, such as `CODEGUARD_JUDGE__PROVIDER` for `judge.provider`. An unset or
   empty variable changes nothing.
2. `.codeguard/config.yaml`, or the file `CODEGUARD_CONFIG` names.
3. The default in [Settings](#settings).

CI uses the environment to name its judge, since it has no subscription; the project
config needs no line for it. These variables configure codeguard reviewing a project,
this repository included; codeguard's own pytest LLM tests and skill evals don't read
them.

## Environment variables

Besides the `CODEGUARD_` overrides, variables choose the config file or the codeguard to
run, sign the judge in, or turn on telemetry:

| Variable | Default | What it does |
|---|---|---|
| `CODEGUARD_JUDGE__PROVIDER` | unset: the file's `judge.provider`, else `claude-cli` | Which provider judges: `claude-cli`, `codex-cli`, `bedrock` or `gemini`; CI sets `bedrock` or `gemini`. See [Which judge runs](#which-judge-runs). |
| `CODEGUARD_JUDGE__MODEL` | unset: the file's `judge.model`, else the package's, else none | The model for judge rules whose binding names none; CI sets the one it judges with. |
| `CODEGUARD_CONFIG` | `.codeguard/config.yaml` | The config file to load, relative to the repository root, such as a gitignored `codeguard.local.yaml` for working on a local package. |
| `CODEGUARD` | the codeguard the plugin ships | The codeguard the hooks run instead, such as a checkout's `.venv/bin/codeguard`. |
| `AWS_DEFAULT_REGION`, and the credentials boto3 finds | the AWS CLI's own | How Bedrock signs in, locally and in CI; see [Bedrock](judges.md#bedrock). |
| `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` | unset | Where Gemini runs, for a `gemini` binding, unless `judge.project` and `judge.location` set it; see [Gemini on Google Cloud](judges.md#gemini-on-google-cloud). |
| `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_API_KEY` | Application Default Credentials | How Gemini signs in: a service account key file, or an API key a proxy adds. |
| `LOGFIRE_TOKEN` | none: nothing is sent | Sends a trace of each run to Logfire; see [Telemetry](telemetry.md). |

## No setting on purpose

- **Judge errors fail the review.** A judge call that couldn't complete, including one
  cut off by the time limit, is reported at its rule's severity, so for an `error` rule
  it fails CI. A rule the judge couldn't check is code nobody checked, and a warning in
  a passing check goes unseen: if a setting could turn these into warnings for a
  project, a broken judge, an expired token or a codeguard bug would let every PR
  through. A bypass is always for one PR ([CI](add-codeguard.md#ci)); the Stop hook
  shows judge failures to you instead ([How a review works](how-a-review-works.md)).
- **A bound rule's judge model.** A rule whose binding names a model is judged with it,
  the one its rule eval passed on alone. A project's `judge.model` applies to every
  other rule, over a package's default ([Which judge runs](#which-judge-runs)).
