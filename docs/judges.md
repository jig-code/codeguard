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
either, codeguard passes the CLI no model, so the CLI's own default judges. A model with
no provider named is run with `claude-cli`, so it must be a Claude model. Every
provider but `claude-cli` needs a model, and a provider can't run another vendor's model,
such as `codex-cli` with a Claude model; codeguard reports each of these as a config
error before it judges. This page says how to set each provider up.

## Choose a provider

- `claude-cli`, the default, runs Claude through the `claude` CLI: on the developer's own
  subscription at the agent's Stop, and in CI with the token the action takes
  ([CI](add-codeguard.md#ci)).
- `codex-cli` runs a GPT model through the `codex` CLI on a ChatGPT subscription
  ([Codex locally](#codex-locally)).
- `gemini` runs Gemini on Vertex AI with Google credentials
  ([Gemini on Google Cloud](#gemini-on-google-cloud)).
- `bedrock` runs Claude or a GPT model on Amazon Bedrock with AWS credentials
  ([Bedrock](#bedrock)).

`codeguard eval --provider` and `--model` judge a rule's eval with another provider and
model whatever its binding names ([CLI](cli.md#eval)); reviews still use the binding's.

## Codex locally

Set a judge rule's binding to `codex-cli` and name its model:

```yaml
skill: .codeguard/skills/responsibility-placement
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
skill: .codeguard/skills/responsibility-placement
paths: ["app/**/*.py"]
provider: bedrock
model: us.openai.gpt-6-luna
```

## Gemini on Google Cloud

A judge rule whose binding sets `provider: gemini` is judged with Gemini on Google Cloud
(Vertex AI):

```yaml
skill: .codeguard/skills/responsibility-placement
paths: ["app/**/*.py"]
provider: gemini
model: gemini-4-argon
```

`judge.calls_at_once` in `.codeguard/config.yaml` sets how many Gemini calls run at once:

```yaml
judge:
  calls_at_once: 2                # Gemini only; default: 2
```

Use the model in the example: codeguard supports only the Gemini model it is tested with.

Where Gemini runs and how it signs in come only from codeguard's environment variables,
not from Google's own settings, so codeguard can sign in differently from your other Google
Cloud tools:

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
