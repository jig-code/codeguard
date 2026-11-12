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
model: gemini-3.1-pro-preview
```

`judge` in `.codeguard/config.yaml` sets where Gemini runs and how many calls run at once:

```yaml
judge:
  project: my-project             # default: GOOGLE_CLOUD_PROJECT
  location: global                # default: GOOGLE_CLOUD_LOCATION, then global
  calls_at_once: 2                # Gemini only; default: 2
```

Use `gemini-3.1-pro-preview`, the Gemini model codeguard was tested with. Flash was
unreliable in testing. Gemini 4 Argon was as accurate, but some of its requests took 15
to 37 s, where 3.1 Pro's longest of 79 took 13 s (median 6.5 s).

codeguard signs in with
[Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc).
It needs the Vertex AI API enabled in the project
([Set up a project](https://cloud.google.com/vertex-ai/docs/start/cloud-environment)), and
credentials with the Vertex AI User role (`roles/aiplatform.user`): your own on your
machine, and a [service account](https://cloud.google.com/iam/docs/service-accounts-create)
elsewhere, through `GOOGLE_APPLICATION_CREDENTIALS` or, in GitHub Actions,
`google-github-actions/auth` before the codeguard action.

Where a proxy adds credentials to requests, as Claude Code cloud environments' network
secrets do, use an [API key](https://cloud.google.com/docs/authentication/api-keys) bound
to the service account instead, restricted to the Agent Platform API, and set
`GOOGLE_API_KEY=proxy-injected`. codeguard then signs in with the key in place of
Application Default Credentials, and calls Gemini in the project and location set above.
Have the proxy send the key as the `x-goog-api-key` header to the Vertex AI endpoint for
that location
([Vertex AI locations](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations)).

## Bedrock

`provider: bedrock` judges with Claude, or a GPT model, on Amazon Bedrock. The model is a Bedrock inference profile, such as
`us.anthropic.claude-haiku-5-5`, and the AWS account must have access to it. codeguard
signs in with the credentials and region (`AWS_DEFAULT_REGION`)
[boto3 finds](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html):
the AWS CLI's on your machine, and the job's in CI.
