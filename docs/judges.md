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
judged it with ([Write a rule package](rule-packages.md)).

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

The judge uses Codex's native repository tools in the read-only sandbox, with project
instructions, hooks, plugins, memories and web search disabled. Temporary files hold
the shared judge instructions, verdict schema and final response; they are removed
after each call. The provider uses `high` reasoning effort and the existing review
deadline. Authentication failures, capacity errors and other process errors fail
immediately, without retries or a separate per-call time limit.

Codex uses the existing verdict cache keyed on the judge inputs and reviewed source,
when a model is named: the `codex` CLI doesn't expose its default model, so with none
named its verdicts aren't cached.
Its native tools discover related repository code as the rule requires. Native events
do not provide complete file-read tracking, so Codex does not populate `loaded_files`
for additional context-file invalidation. Claude and Gemini tracking are unchanged.
Concurrency follows the CLI limit, one call per CPU.

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

Each provider has its own limit on calls at once (`judge.calls_at_once` for Gemini; at
most 2 for Bedrock), so Claude and Gemini rules in one review don't wait on each other. A request that Gemini turns away
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

## Bedrock

Set `bedrock` as the provider and name the model by its vendor's id, such as
`claude-haiku-5-5` or `gpt-6-luna`. codeguard sends it as the cross-region inference
profile `<prefix>.<vendor>.<id>`, with the prefix from `judge.bedrock.inference_prefix`
(`us` unless set). An account that must route through an application inference profile
names that profile's ARN as the model instead; the profile needs a `ModelId` tag naming
the model it routes to ([How a model is named](judge-design.md#how-a-model-is-named)).

codeguard signs in to Bedrock as boto3 does: the AWS CLI's credentials and region on your
machine, and the job's credentials in CI. In GitHub Actions, use
`aws-actions/configure-aws-credentials` before the codeguard action, with a role that
can invoke the model and, for an application inference profile, read its tags
(`bedrock:ListTagsForResource`). [CI](add-codeguard.md#ci) shows the job.
