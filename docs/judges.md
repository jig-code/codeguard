# Choose a judge

A judge rule is judged with the same provider and model in reviews and in its rule eval,
so its rule eval passes on the model that judges it in reviews. The provider and the model
are each taken from the first of these that names it:

1. the rule's binding ([A judge rule's binding](rule-formats.md#a-judge-rules-binding));
2. the project: `CODEGUARD_JUDGE__PROVIDER` and `CODEGUARD_JUDGE__MODEL`, or else
   `judge.provider` and `judge.model` in `.codeguard/config.yaml`
   ([Configuration reference](configuration.md#settings));
3. the rule's package: `judge` in its `codeguard-package.yaml`
   ([Rule packages](rule-packages.md)).

With no provider named, a rule is judged through the `claude` CLI. With no model named
either, codeguard passes the CLI no model, so the CLI's own default judges. A model is
named once, and codeguard never infers its provider from the model's name: a model
needs a provider named. Every provider but `claude-cli` needs a model, and a provider
can't run another vendor's model, such as `codex-cli` with a Claude model; codeguard
reports each of these as a config error before it judges. This page says how to set each
provider up.

Which judge runs is configuration, never code that knows where it runs, so that one or
two config values swap the judge for the whole system and switching models takes
minimal effort.

## What differs by provider

Every judge gets the same instructions, prompt and verdict schema. `gemini` and `bedrock`
ask for the verdict in the output mode pydantic-ai picks for the model, and give each
request to the model `judge.request_time_limit_seconds`, 120 by default, its retries
included. A request still unanswered after 60 seconds has stalled at the provider, so the
judge sends it again.

What differs is only what a provider requires: how codeguard reaches the model (a CLI it
runs, or an API it signs in to), the form of the verdict schema a CLI accepts, and how
codeguard reads each CLI's output. Every judge records the same telemetry keys where its
provider reports the data: `input_tokens`, `output_tokens`, `cache_read_input_tokens`,
`thinking_tokens` and `tool_calls`, plus `num_turns` from all but the `codex` CLI, which
doesn't report it.

### Thinking

How hard a judge's model thinks before its verdict is set per provider, for every rule it
judges, in `.codeguard/config.yaml`:

```yaml
judge:
  thinking:
    claude-cli: high     # default: default
    codex-cli: medium    # default: default
    gemini: medium       # default: medium
    bedrock: xhigh       # default: medium
```

Each provider takes its own levels, or `default`:

| Provider | Levels | Unset | Passed as |
|---|---|---|---|
| `claude-cli` | `low`, `medium`, `high`, `xhigh`, `max` | `default` | `--effort` on the `claude` command line |
| `codex-cli` | `low`, `medium`, `high` | `default` | `model_reasoning_effort` on the `codex` command line |
| `gemini`, `bedrock` | `minimal`, `low`, `medium`, `high`, `xhigh`, `max` | `medium` | pydantic-ai's `thinking` setting |

`default` passes no level, as codeguard passes no model when none is named, so the CLI or
model thinks at its own default. pydantic-ai maps an API level to the model's own thinking
or reasoning setting, and to the nearest level a model offers when it lacks one: Gemini
has no level above `high`, so `xhigh` and `max` think at `high` there. A level a provider
doesn't take is a config error.

The level changes verdicts, so it is set only in the committed config, never in the
environment, and it keys cached verdicts: changing it judges afresh.

## Choose a provider

- `claude-cli`, the default, runs Claude through the `claude` CLI on the developer's own
  subscription at the agent's Stop. It is for local work: CI never uses a subscription or
  a CLI tool, so a CI job judges with `gemini` or `bedrock`.
- `codex-cli` runs a GPT model through the `codex` CLI on a ChatGPT subscription
  ([Codex locally](#codex-locally)).
- `gemini` runs Gemini on Vertex AI with Google credentials
  ([Gemini on Google Cloud](#gemini-on-google-cloud)).
- `bedrock` runs Claude or a GPT model on Amazon Bedrock with AWS credentials
  ([Bedrock](#bedrock)).

`gemini` and `bedrock` run on Linux and macOS, not Windows.

`codeguard eval --provider` and `--model` judge a rule's eval with another provider and
model whatever its binding names ([CLI](cli.md#eval)); reviews still use the binding's.

## Codex locally

Set a judge rule's binding to `codex-cli` and name its model:

```yaml
rule: responsibility-placement
paths: ["app/**/*.py"]
provider: codex-cli
model: gpt-6-luna
```

Install the [Codex CLI](https://developers.openai.com/codex/cli) and sign in with your
ChatGPT subscription. This provider requires ChatGPT authentication; it does not fall
back to API billing. Other providers do not require Codex to be installed. Use a current
CLI supporting `--ignore-user-config`, `--ignore-rules` and `--ephemeral`.

For GPT models in CI, bind the rule to `bedrock` with a Converse model id, inference
profile id or ARN ([Bedrock](#bedrock)). This path uses metered AWS billing and does not
invoke the Codex CLI:

```yaml
rule: responsibility-placement
paths: ["app/**/*.py"]
provider: bedrock
model: us.openai.gpt-6-luna
```

## Gemini on Google Cloud

A judge rule whose binding sets `provider: gemini` is judged with Gemini on Google Cloud
(Vertex AI):

```yaml
rule: responsibility-placement
paths: ["app/**/*.py"]
provider: gemini
model: gemini-4-argon
```

`judge.calls_at_once` in `.codeguard/config.yaml` sets how many Gemini or Bedrock calls
run at once:

```yaml
judge:
  calls_at_once: 2                # Gemini and Bedrock; default: 2
```

Use the model in the example: codeguard supports only the Gemini model it is tested with.

codeguard reads where Gemini runs and how it signs in from these environment variables:

```sh
CODEGUARD_JUDGE__GEMINI__PROJECT=my-project
CODEGUARD_JUDGE__GEMINI__LOCATION=global                      # default: global
CODEGUARD_JUDGE__GEMINI__CREDENTIALS_FILE=/path/to/key.json   # or:
CODEGUARD_JUDGE__GEMINI__API_KEY=...
```

See [Set up a project](https://cloud.google.com/vertex-ai/docs/start/cloud-environment)
for the project. codeguard signs in as a
[service account](https://cloud.google.com/iam/docs/service-accounts-create) with the
Vertex AI User role (`roles/aiplatform.user`), with one of:

- its [key file](https://cloud.google.com/iam/docs/keys-create-delete), in
  `CODEGUARD_JUDGE__GEMINI__CREDENTIALS_FILE`;
- an [API key](https://cloud.google.com/docs/authentication/api-keys) bound to it, in
  `CODEGUARD_JUDGE__GEMINI__API_KEY`.

Setting both is a config error. So is judging with Gemini without a project or a sign-in:
the error names the variable to set.

## Bedrock

`provider: bedrock` judges with Claude, or a GPT model, on Amazon Bedrock. The model is a Bedrock inference profile, such as
`us.anthropic.claude-haiku-5-5`, and the AWS account must have access to it. codeguard
signs in with the credentials and region (`AWS_DEFAULT_REGION`)
[boto3 finds](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html):
the AWS CLI's on your machine, and the job's in CI.
