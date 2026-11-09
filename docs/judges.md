# Choose a judge

### Judge with Codex locally

Set a judge rule's binding to `codex-cli` and name its model:

```yaml
skill: skills/responsibility-placement
paths: ["app/**/*.py"]
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

For GPT models in CI, use the existing `bedrock` provider with a supported Converse
model ID, inference profile ID or ARN. AWS credentials and region resolve as before;
this path uses metered AWS billing and does not invoke the Codex CLI:

```yaml
skill: skills/responsibility-placement
paths: ["app/**/*.py"]
provider: bedrock
model: us.openai.gpt-6-luna
```

The AWS account must have access to the chosen model. Existing Claude, Gemini and
Bedrock defaults and rule bindings are unchanged.

### Judge with Gemini on Google Cloud

By default the judge runs `claude -p`. A judge rule whose binding sets
`provider: gemini` is judged with Gemini on Google Cloud (Vertex AI) instead, in reviews
and in its rule eval, so its rule eval has to pass on Gemini. `codeguard eval --provider
gemini` judges a rule's eval with Gemini whatever its binding names:

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

`provider: bedrock` judges with Claude on Amazon Bedrock through the same tools, for a
run that must be Claude. boto3 finds the credentials and region (`AWS_DEFAULT_REGION`)
as the AWS CLI does, and the model is a Bedrock inference profile such as
`us.anthropic.claude-haiku-5-5`.

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
