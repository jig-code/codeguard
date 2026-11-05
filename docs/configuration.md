# Configuration

## Rules

A project's own rules live under `.codeguard/`, in the layout
[Write a rule package](rule-packages.md) describes. To write or change one, use the
plugin's [writing-rules skill](../skills/writing-rules/SKILL.md). The two kinds of rule
are in [Rules](architecture.md#rules).

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
      - uses: jig-code/codeguard@v0.11.0
        with:
          packages-token: ${{ secrets.CODEGUARD_PACKAGES_TOKEN }}
```

## Configure the judge

[Judge configuration](architecture.md#judge-configuration) says how codeguard picks the
provider and model for each rule: the binding, else the project's default, else the
package's; how a model is named on each provider; and how the environment variables
`CODEGUARD_JUDGE__PROVIDER` and `CODEGUARD_JUDGE__MODEL` override the project's config,
which is how CI names its judge. The keys:

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
([CI](add-codeguard.md#ci)). This path uses metered AWS billing and does not invoke the
Codex CLI:

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
requests without a verdict is reported as not judged.

Each provider has its own limit on calls at once (`judge.calls_at_once` for Gemini), so
Claude and Gemini rules in one review don't wait on each other. A request that Gemini turns away
(408, 429 or a 5xx) or whose connection breaks is sent again for about 15 seconds, and
then the rule is reported as not judged.

Use `gemini-3.1-pro-preview`, the Gemini model codeguard was tested with. Flash was
unreliable in testing. Gemini 4 Argon was as accurate, but some of its requests took 15
to 37 s, where 3.1 Pro's longest of 79 took 13 s (median 6.5 s).

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
| `review_time_limit_minutes` | `5` | The review stops judging after this long. Each rule and file it didn't judge gets a `judge_error` diagnostic at the rule's severity, as a failed judge call does. The GitHub Action stops the review 2 minutes after it. | A stuck `claude` call once hung a CI review for 30 minutes with no output. A limit turns a hang into a visible failure. |
| `ast-grep` | the version codeguard installs | The ast-grep version every pattern rule and gate runs with, through `uv tool run`. | One version for every rule, so a rule matches the same code on every machine. codeguard fails when it is outside a package's `ast-grep` range. |
| `packages` | none | The rule packages and rulesets the project uses; see [Rules](#rules). Without it, only the rules in `.codeguard/` run. | A project opts into each ruleset, so no rule runs that the project didn't choose. |
| `packages[].rulesets.<name>`: `include`, `exclude`, `severity`, `ci_only`, `rules.<id>` | every rule, at its own severity, in every review | Which of a ruleset's rules run, where, and at what severity; see [Rules](#rules). | |
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
  through. A bypass is always for one PR ([CI](add-codeguard.md#ci)); the Stop hook
  shows judge failures to you instead ([What the hooks check](hooks.md)).
- **A bound rule's judge model.** A rule whose binding names a model is judged with it,
  the one its rule eval passed on alone. A project's `judge.model` applies to every
  other rule, over a package's default ([Configure the judge](#configure-the-judge)).

Settings that decide what a review reports belong in the committed config, not in the
environment, so CI and every machine review a commit the same way. Environment variables
only choose the config file or the codeguard to run, sign the judge in, turn on
telemetry, or name the judge, which CI must do since it has no subscription
([Judge configuration](architecture.md#judge-configuration) says how they override the
file):

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
