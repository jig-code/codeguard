**The judge** grades one rule against one file's change. The providers are the `claude`
CLI in safe mode and the `codex` CLI in a read-only sandbox (Claude and GPT on the
developer's subscription), and Amazon Bedrock (Claude and GPT) and Gemini on Vertex AI
(both pydantic-ai, with equivalent tools). Judge configuration, below, says which one
judges a rule.

- Its input: the judge template, which holds the instructions; the skill text; the
  `changes` element, an excerpt of the changed code with `+`, space and `-` marks and the
  file's own line numbers; and the tools Read, Grep and Glob over the repository at the
  change.
- What it reads: the prompt holds what the judge will certainly need. The judge decides
  from the rule what else to read, and reads it with its tools. The prompt never says
  what to read or when. When a model fails to read what an obvious case needs, that is a
  finding about the model, not a reason to change the prompt.
- Its output: a reason for its verdict, pass or fail, saying what in the changed code
  keeps the rule or breaks it, as context for whoever troubleshoots the verdict;
  and violations, each with a file, line, message and confidence (1.0, 0.9, 0.7 or 0.5).

### Judge configuration

A rule's provider and its model resolve separately, each from the rule's binding, else
the project's default, else the rule package's default (what the package's rules were
written and evaluated against). [Configure the
judge](configuration.md#configure-the-judge) states the rule, with its defaults and the
eval overrides. codeguard passes a resolved model explicitly.

The project config is a pydantic-settings model. Its sources, in priority order:
environment variables, then `.codeguard/config.yaml`, then field defaults. codeguard
passes the file's values to the model, which places them below the environment, and
nothing ranks above the environment. An environment variable named after any key
overrides the file: with the prefix `CODEGUARD_` and `__`
between the parts of a nested key, `CODEGUARD_JUDGE__PROVIDER` is `judge.provider` and
`CODEGUARD_JUDGE__MODEL` is `judge.model`. That is the whole CI mechanism: the CI workflow sets them to `bedrock` or
`gemini` with the model, and the project config needs no line for it. An unset variable
means nothing: the file's value stands, or the key is absent and the next level applies.
The variables configure codeguard reviewing a project in CI, codeguard reviewing itself
included; codeguard's pytest LLM tests and skill evals are a different configuration,
unchanged by them. In CI, Bedrock signs in with AWS credentials and Vertex AI with a
service account.

Global settings stay global, in `.codeguard/config.yaml`: the default model,
`calls_at_once` (Gemini only), the Vertex AI project and location, and the Bedrock
inference prefix. codeguard is driven by a provider and a model, and nothing else names
the model a request runs.

A model is named once, by the id its vendor gives it, and each provider maps that id onto
its own API. A model may instead be named by the provider's own id, such as a Bedrock
application inference profile's ARN, which the provider passes through as is, as the
`claude` CLI's `--model` does:

- A Claude model is named by its Anthropic id, the one the `claude` CLI takes:
  `claude-haiku-5-5`. A GPT model is named by its OpenAI id, the one the `codex` CLI
  takes: `gpt-6-luna`. A CLI sends the id as is. The Bedrock provider names it to
  pydantic-ai as the cross-region inference profile `<prefix>.<vendor>.<id>`, the vendor
  `anthropic` for a Claude model and `openai` for a GPT model:
  `us.anthropic.claude-haiku-5-5`, `us.openai.gpt-6-luna`. The prefix is the project's
  `judge.bedrock.inference_prefix` (`us` unless set; pydantic-ai also lists `global`,
  `eu`, `au` and `jp`). Any other id, such as an application inference profile's ARN for
  an account that must route through one, is Bedrock's own and is sent as the request's
  `modelId` as is. An application inference profile's ARN names no model, so the provider
  reads the model it routes to from the profile's `ModelId` tag
  (`bedrock:ListTagsForResource`, once per profile) and calls pydantic-ai as that model. So `judge: {model: claude-haiku-5-5}` as a package default judges with Haiku
  5.5 on the CLI locally and on Bedrock in CI, with no other change, in a project that
  sets no model of its own.
- A Gemini model is named by its Vertex AI id, `gemini-3.1-pro-preview`, and runs with
  `provider: gemini`.
- `provider` names where the model runs: `claude-cli` (the default) or `bedrock` for a
  Claude model, `codex-cli` or `bedrock` for a GPT model, `gemini` for a Gemini model.
  Any model that isn't a Claude model needs `provider` set: with none, it is a
  configuration error that says to set it. A provider the surface can't use is an error,
  never a fallback.

A rule package's CI runs its model matrix with `codeguard eval --provider` and
`--model`, today over Gemini on Vertex AI and Claude Haiku 5.5 on Bedrock.

## Judge input

The judge request and the verdict schema belong to the core; a provider only maps them
onto its API.

- **Input.** The prompt embeds exactly what the judge will certainly have to read, and
  nothing it only might need; the judge reads the rest with its tools. The changed code
  is:
  - each changed function or method, with its decorators;
  - each changed statement outside them, whole, with the header and decorators of the
    class it's in (not the class's other members);
  - for a changed `elif`, `else`, `except` or `finally` line, just that clause (an
    `except` with its `try` and the block it guards);
  - each changed comment or docstring line alone, since prose breaks no code rule (such a
    line also gates only as `comment` or `docstring`);
  - each class whose header changed, whole;
  - the whole of each node of the rule's triggers around the change.

  Lines carry the file's own line numbers. Removed lines are placed using the base
  version's parse, and bring in the code the change kept around them in the same way:
  their function, their class's header, the rest of their statement, or the header of
  the statement whose block they were in (a removed `except` brings its `try` and the
  block it guarded), never the code beside them. Removed lines gate on their own kinds. A
  renamed file is compared with its old path. Added and changed lines are marked `+`;
  removed lines are marked `-`. For a language without a syntax table, the changed lines
  are sent; for a new file, or with `--all`, the whole file is sent. The template tells
  the judge that the whole file is at its path, and to read it, or any other file, when
  the rule needs more.
- **Isolation.** The `claude` CLI provider runs `claude --safe-mode`, which also leaves
  out MCP servers and memory, and runs no subagents. The `codex` CLI provider runs
  `codex exec` in a read-only sandbox with project instructions, memories and web search
  off. The Bedrock and Gemini providers have the equivalent tools, rooted at the
  repository.
- **Model.** A full model id, never an alias, so a model change is visible to the cache:
  the cache keys on the id the provider sends, which for Bedrock is the inference profile
  derived from the vendor's id (Judge configuration). When no level names a model, the
  model is still known before any judging: at the start of a run, codeguard reads the
  model the `claude` CLI will run from where the CLI reads it (`ANTHROPIC_MODEL`, then the
  `env` and then the `model` of its managed, local, project and user settings, in that
  order), and when those name none, or only an alias such as `opus`, it makes one small
  CLI call that reports it. Every verdict in the run is keyed on that model, so a change of
  the CLI's default model is never served a verdict of the old one. A dry run never makes
  that call. The `codex` CLI doesn't expose its default model, so with no model named its
  verdicts aren't cached.
- **Output.** Validated against the verdict schema; output that fails validation is an
  internal error.
- **Confidence scale**, stated in the verdict schema: 1.0 when the judge is certain the
  code breaks the rule and nothing in the working directory points to an allowed
  exception; 0.9 when the code breaks the rule as written but the verdict rests on a
  reading of the rule's terms a reviewer could contest; 0.7 when something in the working
  directory points to an allowed exception; 0.5 when a violation is as likely as not;
  below 0.5, not reported. The scale never rewards resemblance to an example: rules hold
  none.
- **Determinism.** Claude Code adds the date, the account and the working directory
  to the message. Those are the only inputs codeguard doesn't control.
