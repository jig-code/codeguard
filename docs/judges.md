# Choose a judge

A judge rule is judged by a provider and a model. [Which judge
runs](configuration.md#which-judge-runs) says which level names them; this page says how
to set each provider up.

## Choose a provider

- `claude-cli`, the default, runs Claude through the `claude` CLI on the developer's own
  subscription. It suits the agent's Stop hook and needs nothing beyond Claude Code.
- `codex-cli` runs a GPT model through the `codex` CLI on a ChatGPT subscription
  ([Codex locally](#codex-locally)).
- `bedrock` runs Claude or a GPT model on Amazon Bedrock with AWS credentials
  ([Bedrock](#bedrock)). CI uses it, since CI has no subscription.
- `gemini` runs Gemini on Vertex AI with Google credentials
  ([Gemini on Google Cloud](#gemini-on-google-cloud)).

Name the model a rule's eval passed on: a rule passes only on the models its eval has
judged it with ([Write rules](write-rules.md)).

## Codex locally

Set `codex-cli` as the provider, in the project's `judge` default or a rule's binding.
Name a model to pass it; with none, the `codex` CLI uses its own default
([Which judge runs](configuration.md#which-judge-runs)):

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

The existing evaluation override also accepts Codex:

```sh
codeguard eval --provider codex-cli --model gpt-6-luna
```

For GPT models in CI, the workflow sets the `bedrock` provider, as for Claude
([Bedrock](#bedrock)). This path uses metered AWS billing and does not invoke the
Codex CLI:

```yaml
env:
  CODEGUARD_JUDGE__PROVIDER: bedrock
  CODEGUARD_JUDGE__MODEL: gpt-6-luna
```

The AWS account must have access to the chosen model.

## Gemini on Google Cloud

A judge rule whose binding, package or project sets `provider: gemini` is judged with
Gemini on Google Cloud (Vertex AI), in reviews and in its rule eval, so its rule eval has
to pass on Gemini. `codeguard eval --provider gemini` judges a rule's eval with Gemini
whatever is configured:

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
  location: global                # default: GOOGLE_CLOUD_LOCATION
  calls_at_once: 2                # Gemini only; default: 2
```

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

## Bedrock

Set `bedrock` as the provider and name the model by its vendor's id, such as
`claude-haiku-5-5` or `gpt-6-luna`. codeguard sends it as the cross-region inference
profile of the geography of the AWS region boto3 finds (`AWS_REGION`), such as
`us.anthropic.claude-haiku-5-5` in `us-west-2`. An account that must route through an application inference profile
names that profile's ARN as the model instead; the profile needs a `ModelId` tag naming
the model it routes to ([How a model is named](configuration.md#how-a-model-is-named)).

codeguard signs in to Bedrock as boto3 does: the AWS CLI's credentials and region on your
machine, and the job's credentials in CI. In GitHub Actions, use
`aws-actions/configure-aws-credentials` before the codeguard action, with a role that
can invoke the model and, for an application inference profile, read its tags
(`bedrock:ListTagsForResource`). [CI](add-codeguard.md#ci) shows the job.
