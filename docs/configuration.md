# Configuration

## Rules

A project's own rules live under `.codeguard/`. To write or change one, use the
plugin's `writing-rules` skill: it says which kind of rule fits a convention, how to
state the rule, and how to test it. These docs document the files and commands the
skill works with.

A rule is one of two kinds:

- A **pattern rule** is an ast-grep rule. It matches code by its syntax tree.
- A **judge rule** is a skill that Claude judges each change to a file against.

A project can also opt into rulesets from rule packages:

```yaml
# .codeguard/config.yaml
packages:
  - kind: git
    git: https://github.com/betterwithranch/codeguard-rules.git
    ref: v0.6.0
    rulesets:
      python:
        exclude: [no-del-param]
        rules:
          names-match-behavior:
            paths: ["src/**/*.py"]
            severity: warning
```

- Only the listed rulesets run.
- `include` lists the only rules that run, pattern and judged; rules the package adds
  later stay off. `exclude` turns rules off. Set one or the other.
- `rules.<id>` overrides a rule's `paths`, `exclude_paths`, `severity` or `ci_only`.
  `exclude_paths: []` brings back the files its binding leaves out. A project doesn't
  override the model a binding names: the rule's evals passed on it. The project's own
  `judge` default applies to every other rule, over a package's default ([Configure the
  judge](#configure-the-judge)).
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
- `kind: path` with `path: ../my-rules` in place of `git` uses a local package, for
  working on one. To use it without editing the committed config, put that config in a
  gitignored file such as `codeguard.local.yaml` and set
  `CODEGUARD_CONFIG=codeguard.local.yaml`. The path is relative to the repository root.

Diagnostics name a packaged rule by package, ruleset and id:
`betterwithranch/python/no-del-param`.

A git package's `ref` is a tag or commit. Local and CI reviews use the rules at that
`ref`, so a commit gets the same rules everywhere, and a package release changes nothing
until a project moves its `ref`. To try a release, change `ref` locally, or point a
`kind: path` package at a checkout of it.

codeguard fetches each `ref` once into `~/.cache/codeguard/packages` and reuses it, so a
`ref` must not be a branch.

A project runs one ast-grep version for all its rules: codeguard's own, or the version
`.codeguard/config.yaml` sets, which runs through `uv tool run`:

```yaml
ast-grep: 0.45.3
```

codeguard fails when that version is outside a package's `ast-grep` range.

For a private package in CI, pass a token that can read it:

```yaml
      - uses: jig-code/codeguard@v0.9.1
        with:
          packages-token: ${{ secrets.CODEGUARD_PACKAGES_TOKEN }}
```

## Configure the judge

Which provider and model judge a rule is configuration, never code that knows where
the review runs. codeguard resolves it in this order, and the first level that names a
model wins:

1. The rule's binding, `provider` and `model` ([The binding](rule-packages.md#the-binding)): a per-rule
   override for a rule whose eval passes on one model alone.
2. The project's default, `judge` in `.codeguard/config.yaml`.
3. The rule package's default, `judge` in `codeguard-package.yaml`.

When no level names a model, codeguard runs the provider's CLI on your subscription
(the `claude` CLI unless `codex-cli` is configured) with no `--model` flag, so the CLI's
own default judges, as it does when you use it; codeguard has no built-in model of its
own. When a level names one, codeguard passes it
explicitly. A Bedrock or Vertex AI run needs a model named by configuration. The
configuration drives it. `codeguard eval --provider` and `--model` override every level
for that run.

The project config is read with pydantic-settings, so an environment variable named
after a key overrides the file: `CODEGUARD_` plus the key path with `__` between its
parts, `CODEGUARD_JUDGE__PROVIDER` for `judge.provider` and `CODEGUARD_JUDGE__MODEL`
for `judge.model`, and so for any `judge` key. That is the whole CI mechanism: the CI
workflow sets the two variables, to `bedrock` or `gemini` with the model, and the
project config needs no line for it. An unset variable means nothing: the file's value
stands, or the key is absent and the next level applies, a package's default or the
`claude` CLI with its own default. CI never uses a subscription or the `claude` CLI: it
judges through pydantic-ai on Bedrock or Vertex AI with the environment's credentials
([CI](add-codeguard.md#ci)). This configures codeguard reviewing a
project in CI, codeguard reviewing itself included; codeguard's own LLM tests and skill
evals are a different configuration and don't use it.

```yaml
# codeguard-package.yaml: the package's default for its judge rules
judge:
  model: claude-haiku-5-5

# .codeguard/config.yaml: the project's default, and the settings that stay global
judge:
  model: claude-sonnet-5-5          # for rules whose binding names none, over a package's default
  provider: bedrock                 # claude-cli (default) or bedrock for Claude; codex-cli or bedrock for GPT
  bedrock:
    inference_prefix: us            # the cross-region inference profile's prefix; default us
    # inference_profile: arn:aws:bedrock:…:application-inference-profile/…  # routes through this ARN instead
  project: my-project               # Vertex AI; default GOOGLE_CLOUD_PROJECT
  location: global                  # default GOOGLE_CLOUD_LOCATION
  calls_at_once: 2                  # Gemini only
```

A model is named once, by the id its vendor gives it, and each provider maps it onto
its API. A Claude model is named by its Anthropic id, the one the `claude` CLI takes
(`claude-haiku-5-5`), and a GPT model by its OpenAI id, the one the `codex` CLI takes
(`gpt-6-luna`). A CLI sends the id as is, and the Bedrock provider sends the
cross-region inference profile `<prefix>.<vendor>.<id>`, `anthropic` for Claude and
`openai` for GPT (`us.anthropic.claude-haiku-5-5`, `us.openai.gpt-6-luna`), or, when
`inference_profile` is set, that ARN as the request's model id. A Gemini model is named
by its Vertex AI id (`gemini-3.1-pro-preview`) and always runs on Vertex AI, so it needs
no `provider`. A Claude model runs on `claude-cli` (the default) or `bedrock`; a GPT
model needs `provider` set, `codex-cli` or `bedrock`, and with none it is a
configuration error that says to set it. A package default of `claude-haiku-5-5`
therefore judges with Haiku 5.5 through the CLI on your machine and on Bedrock in CI,
with no other change, in a project that sets no model of its own. Verdicts are cached
by the id the provider sends, so switching
providers never reuses another's verdicts.

Switching the judge is one or two values: `judge.model` and, for Bedrock or a GPT
model, `judge.provider`.

## Judge with Codex locally

Set `codex-cli` as the provider, in the project's `judge` default or a rule's binding.
Name a model to pass it; with none, the `codex` CLI uses its own default
([Configure the judge](#configure-the-judge)):

```yaml
# .codeguard/config.yaml
judge:
  provider: codex-cli
  model: gpt-6-luna
```

Install the Codex CLI separately and sign in with `codex login` using your ChatGPT
subscription. CodeGuard invokes `codex exec` with ephemeral sessions, read-only
permissions and the shared verdict schema. This provider requires ChatGPT authentication;
it does not fall back to API billing. Other providers do not require Codex to be installed.
Use a current CLI supporting `--ignore-user-config`, `--ignore-rules` and `--ephemeral`.

The judge uses Codex's native repository tools in the read-only sandbox, with project
instructions, hooks, plugins, memories and web search disabled. Temporary files hold
the shared judge instructions, verdict schema and final response; they are removed
after each call. The provider uses `high` reasoning effort and the existing review
deadline. Authentication failures, capacity errors and other process errors fail
immediately, without retries or a separate per-call time limit.

Codex uses the existing verdict cache keyed on the judge inputs and reviewed source.
Its native tools discover related repository code as the rule requires. Native events
do not provide complete file-read tracking, so Codex does not populate `loaded_files`
for additional context-file invalidation. Claude and Gemini tracking are unchanged.
Concurrency follows the CLI limit, one call per CPU.

The existing evaluation override also accepts Codex:

```sh
codeguard eval --provider codex-cli --model gpt-6-luna
```

For GPT models in CI, the workflow sets the `bedrock` provider, as for Claude
([CI](add-codeguard.md#ci)); the model keeps its OpenAI id, and the Bedrock provider sends
`us.openai.gpt-6-luna`, or the ARN in `judge.bedrock.inference_profile`. AWS
credentials and region resolve as before; this path uses metered AWS billing and does
not invoke the Codex CLI:

```yaml
env:
  CODEGUARD_JUDGE__PROVIDER: bedrock
  CODEGUARD_JUDGE__MODEL: gpt-6-luna
```

The AWS account must have access to the chosen model.

## Judge with Gemini on Google Cloud

A judge rule whose binding, package or project names a Gemini model is judged with
Gemini on Google Cloud (Vertex AI), in reviews and in its rule eval, so its rule eval has
to pass on Gemini. `codeguard eval --provider gemini` judges a rule's eval with Gemini
whatever is configured:

```yaml
skill: .claude/skills/responsibility-placement
paths: ["app/**/*.py"]
provider: gemini
model: gemini-3.1-pro-preview
```

`judge` in `.codeguard/config.yaml` sets where Gemini runs and how many calls run at once:

```yaml
judge:
  project: my-project             # default: GOOGLE_CLOUD_PROJECT
  location: global                # default: GOOGLE_CLOUD_LOCATION
  calls_at_once: 2                # Gemini only; default: 2
```

Gemini reads the working directory through read-only `read_file`, `grep` and `glob`
tools, limited to the repository, thinks at the `LOW` level, and returns its verdict as
structured output with the same verdict schema as Claude. A judgement that makes 10
requests without a verdict is reported as not judged. Verdicts are cached per provider
and model, so switching providers doesn't reuse Claude's verdicts.

Gemini's pay-as-you-go capacity is shared and limited by tokens per minute, so the
gemini provider makes 2 calls at once. Each provider has its own limit, so Claude and
Gemini rules in one review don't wait on each other. A request that Gemini turns away
(408, 429 or a 5xx) or whose connection breaks is sent again for about 15 seconds, and
then the rule is reported as not judged.

Use `gemini-3.1-pro-preview`, the Gemini model codeguard was tested with. Flash was
unreliable in testing. Gemini 4 Argon was as accurate, but some of its requests took 15
to 37 s, where 3.1 Pro's longest of 79 took 13 s (median 6.5 s).

`provider: bedrock` judges a Claude model on Amazon Bedrock through the same tools. It
is CI's judge for Claude models, and a project can set it locally. boto3 finds the
credentials and region (`AWS_DEFAULT_REGION`) as the AWS CLI does. The model is named by
its Anthropic id, `claude-haiku-5-5`, and sent as the inference profile
`judge.bedrock.inference_prefix` builds, `us.anthropic.claude-haiku-5-5` by default;
`judge.bedrock.inference_profile` routes through an application inference profile's ARN
instead ([Configure the judge](#configure-the-judge)).

codeguard signs in with Application Default Credentials. Set it up once per project:

1. Enable the Vertex AI API:
   `gcloud services enable aiplatform.googleapis.com --project my-project`.
2. Create a service account with the Vertex AI User role:
   ```sh
   gcloud iam service-accounts create codeguard --project my-project
   gcloud projects add-iam-policy-binding my-project \
     --member serviceAccount:codeguard@my-project.iam.gserviceaccount.com \
     --role roles/aiplatform.user
   ```
3. Give codeguard the credentials. On your machine, `gcloud auth application-default login`
   is enough. Elsewhere, create a key with
   `gcloud iam service-accounts keys create key.json --iam-account codeguard@my-project.iam.gserviceaccount.com`
   and set `GOOGLE_APPLICATION_CREDENTIALS` to its path. In GitHub Actions, use
   `google-github-actions/auth` before the codeguard action.

Where a proxy adds credentials to requests, as Claude Code cloud environments' network
secrets do, use an API key bound to the service account instead: create it under
**APIs & Services → Credentials** with only Agent Platform API allowed, have the proxy send
it as the `x-goog-api-key` header to `aiplatform.googleapis.com`, and set
`GOOGLE_API_KEY=proxy-injected` with `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`,
`project` and `location` unset. The key identifies the project.

## Telemetry

Set `LOGFIRE_TOKEN` to a Logfire write token and codeguard sends a trace of each run.
Without it, codeguard sends nothing. Set it where the agent runs: your shell profile, or
`env` in `~/.claude/settings.json`.

- `claude judges {rule} on {file}`: one span per Claude call, with `model`, `num_turns`,
  `duration_ms`, `cost_usd`, `input_tokens`, `output_tokens`, `cache_read_input_tokens`,
  `cache_creation_input_tokens`, `thinking_tokens` and `tool_calls`.
- `gemini judges {rule} on {file}`: one span per Gemini judgement, with `model`,
  `num_turns`, `input_tokens`, `output_tokens`, `cache_read_input_tokens` and
  `thinking_tokens`, summed over its requests, and `tool_calls`. Its time starts once the call has a slot,
  not while it waits for one. Inside it, Pydantic AI's spans record each request and
  tool call with its content: the prompt, which holds the rule and the changed
  code, Gemini's thought summaries, the files it read and its verdict.
- `tool_calls` on a Claude or Gemini span is each call the judge made to its read-only
  tools, in order: the tool's name and the arguments it gave, such as the path it read or
  the pattern it searched for. It records a call that failed, and on Gemini, the calls of
  a judgement that returned no verdict. Claude's call that returns the verdict isn't one.
- `judge {rule} on {file}`: one span per rule and file, with `cache_hit`, `violations`,
  `loaded_files` (the files the verdict depends on) and `changed_files` (the loaded files
  that changed since the cached verdict, which is why it was judged again). The Claude or
  Gemini span inside it has that judgement's time and tokens.
- `review {repository}`: `files`, `diagnostics`, `errors`, and `host` (the caller passed
  with `--host`, such as `claude-code` or `codex`).

In CI, pass the token as the action's `logfire-token` input.

## Configuration reference

A project's settings live in `.codeguard/config.yaml`, which is committed, so a commit
gets the same review on every machine and in CI. Every setting is optional.

| Setting | Default | What it does | Why the default |
|---|---|---|---|
| `confidence_threshold` | `0.9` | A judged `error` with a lower confidence is reported as a warning, to you rather than the agent, and doesn't block. | Only findings the judge is sure of should stop an agent or fail a PR. A doubtful finding that blocked would send the agent after a violation that may not exist. See [What the hooks check](hooks.md#what-the-hooks-check). |
| `review_time_limit_minutes` | `5` | The review stops judging after this long. Each rule and file it didn't judge is reported as not checked, at the rule's severity. The GitHub Action stops the review 2 minutes after it. | A stuck `claude` call once hung a CI review for 30 minutes with no output. A limit turns a hang into a visible failure. |
| `ast-grep` | the version codeguard installs | The ast-grep version every pattern rule and gate runs with, through `uv tool run`. | One version for every rule, so a rule matches the same code on every machine. codeguard fails when it is outside a package's `ast-grep` range. |
| `packages` | none | The rule packages and rulesets the project uses; see [Rules](#rules). Without it, only the rules in `.codeguard/` run. | A project opts into each ruleset, so no rule runs that the project didn't choose. |
| `packages[].rulesets.<name>.include` | every rule in the ruleset | The only rules that run. Rules the package adds later stay off. Set it or `exclude`, not both. | |
| `packages[].rulesets.<name>.exclude` | none | Rules that don't run. | |
| `packages[].rulesets.<name>.severity` | each rule's own | The severity of every rule in the ruleset, including rules the package adds later. A rule's own override wins. | `warning` trials a ruleset: its findings print without blocking. |
| `packages[].rulesets.<name>.ci_only` | `false` | Runs every rule in the ruleset only in CI and in reviews run by hand, not in the agent's Stop hook. A rule's own override wins. | A hook review spends the developer's subscription each time an agent stops; `true` keeps a costly rule to CI. See [Rules](#rules). |
| `packages[].rulesets.<name>.rules.<id>` | the binding's | Overrides a rule's `paths`, `exclude_paths`, `severity` or `ci_only`. | |
| `judge.model` | none: the `claude` CLI runs with no `--model`, so its own default judges | The model for judge rules whose binding names none, by its vendor's id, over a package's default; see [Configure the judge](#configure-the-judge). A Bedrock or Vertex AI run needs one named here, in the package or in the binding. | The project decides what judges its code; a package's default covers projects that don't; codeguard has no built-in model of its own. |
| `judge.provider` | `claude-cli` | Where a Claude or GPT model runs: `claude-cli` or `bedrock` for Claude, `codex-cli` or `bedrock` for GPT, which needs it set. A Gemini model needs none. | Which judge runs is configuration, so a switch is one value. CI never uses a subscription: its workflow sets `CODEGUARD_JUDGE__PROVIDER`. |
| `judge.bedrock.inference_prefix` | `us` | The cross-region inference profile prefix Bedrock requests use: `<prefix>.<vendor>.<model>`, `anthropic` or `openai`. | A model is named once, by its vendor's id; where it runs is the environment's. |
| `judge.bedrock.inference_profile` | none | An application inference profile ARN to send as the model id instead. | Some accounts must route through one. |
| `judge.calls_at_once` | `2` | How many Gemini judge calls run at once; other providers aren't limited by it. | Gemini's pay-as-you-go capacity is shared, so fewer calls keep a review under its tokens-per-minute limit. A `claude` call mostly waits on the network, so it follows the machine. |
| `judge.project`, `judge.location` | `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` | Where Gemini runs; see [Judge with Gemini on Google Cloud](#judge-with-gemini-on-google-cloud). | |

Two things have no setting on purpose:

- **Judge errors fail the review.** A judge call that couldn't complete, including one
  cut off by the time limit, is reported at its rule's severity, so for an `error` rule
  it fails CI. A rule the judge couldn't check is code nobody checked, and a warning in
  a passing check goes unseen: if a setting could turn these into warnings for a
  project, a broken judge, an expired token or a codeguard bug would let every PR
  through. A bypass is always for one PR: the `codeguard-allow-judge-errors` label
  ([CI](add-codeguard.md#ci)), which shows in the PR's history. The Stop hook always passes
  `--judge-errors-as-warnings`, because the agent can't fix a judge failure. It shows
  the failure to you, and CI still fails on it.
- **A bound rule's judge model.** A rule whose binding names a model is judged with it,
  the one its rule eval passed on alone. A project's `judge.model` applies to every
  other rule, over a package's default ([Configure the judge](#configure-the-judge)).

Settings that decide what a review reports belong in the committed config, not in the
environment, so CI and every machine review a commit the same way. Environment variables
only choose the config file or the codeguard to run, sign the judge in, turn on
telemetry, or name the judge, which CI must do since it has no subscription. The config
is read with pydantic-settings, so any `judge` key can be set from a variable named
`CODEGUARD_` plus the key path with `__` between its parts, and the variable overrides
the file; an unset variable means nothing:

| Variable | Default | What it does |
|---|---|---|
| `CODEGUARD_JUDGE__PROVIDER` | unset: the file's `judge.provider`, else `claude-cli` | Where a Claude or GPT model runs: `claude-cli`, `codex-cli` or `bedrock`; CI sets `bedrock`. See [Configure the judge](#configure-the-judge). |
| `CODEGUARD_JUDGE__MODEL` | unset: the file's `judge.model`, else the package's, else none | The model for judge rules whose binding names none; CI sets the one it judges with. |
| `CODEGUARD_CONFIG` | `.codeguard/config.yaml` | The config file to load, relative to the repository root, such as a gitignored `codeguard.local.yaml` for working on a local package. |
| `CODEGUARD` | the codeguard the plugin ships | The codeguard the hooks run instead, such as a checkout's `.venv/bin/codeguard`. |
| `AWS_DEFAULT_REGION`, and the credentials boto3 finds | the AWS CLI's own | How Claude on Bedrock signs in, locally and in CI. |
| `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` | unset | Where Gemini runs, for a `gemini` binding, unless `judge.project` and `judge.location` set it; see [Judge with Gemini on Google Cloud](#judge-with-gemini-on-google-cloud). |
| `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_API_KEY` | Application Default Credentials | How Gemini signs in: a service account key file, or an API key a proxy adds. |
| `LOGFIRE_TOKEN` | none: nothing is sent | Sends a trace of each run to Logfire; see [Telemetry](#telemetry). |
