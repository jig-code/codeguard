# codeguard's architecture

This document describes how codeguard works and the invariants its design keeps. A change
to codeguard must keep every invariant here; a change that would break one needs the
maintainers' approval before it is made.

## How codeguard works

### Purpose

codeguard raises the floor of the quality of code that a coding agent (Claude Code or
Codex) writes on its own. It does that by defining rules the agent follows in its
development loop, and by reviewing every change against those rules, with deterministic
checks and an LLM judge, when the agent stops and in CI. Rules cover architecture and
design as well as code-level practice.

### Rules

A rule states one requirement on code and why it matters. A rule is one of two kinds:

- A pattern rule is an ast-grep rule, for a requirement that can be checked mechanically.
  Its note explains why the requirement exists and how to fix a violation.
- A judge rule is a skill (`SKILL.md`), for a requirement that needs judgment. The skill
  states the requirement and why it matters.

Rules live in a project's `.codeguard/` directory or come from rule packages fetched from
git and pinned to a tag.

Use the writing-rules skill's
[tool-selection guidance](../skills/writing-rules/references/choosing-a-tool.md)
to decide whether a requirement belongs to an existing checker, a pattern rule or a
judge rule. Passing one rule does not excuse violations owned by other checks.

### Components

**Bindings** map files to a rule by path globs. A binding sets the rule's severity and
its triggers, and may name its judge provider and model over the project's and the
package's defaults (Judge configuration, below).

**Triggers and gates** decide whether a judge rule runs on a change at all. A judge rule
is called only when the change touches one of its triggers. A trigger is a change kind
(`import`, `function-body`, …) or a gate. A gate is an ast-grep rule that matches where a
violation could appear.

**The review pipeline** runs in the Stop hook, in CI and in `codeguard review`:

1. Take the changeset.
2. Pick the candidate rules.
3. Pattern rules run. A file with a blocking pattern diagnostic skips the judge.
4. Classify (planned): a model call narrows the candidates.
5. The judge makes one call per rule and file.
6. Verify (gated): a second model call confirms each violation.
7. The confidence threshold applies: a violation below 0.9 is reported as a warning,
   never dropped.

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

**The verdict cache** stores verdicts keyed on the template, model, skill, path, changed
code and whole file. When a provider exposes file-read tracking, recorded context-file
changes also invalidate the verdict. Evals and CI never use the cache.

**Host adapters** turn a hook payload into a CLI call, and the CLI's result into a block
or a pass. The only adapter is for the Stop hook. Planned: a pre-edit hook that denies an
edit until the file's skill is loaded.

**The CLI** is the core interface: `review` reviews a changeset; `test` runs pattern rule
and gate tests, with no model; `eval` runs judge rule evals, repeated N times; `config`
prints a setting. The plugin ships the CLI, and the GitHub Action runs it in CI.

### Judge configuration

Which provider and model judge a rule is resolved in this order. The first level that
names a model wins, codeguard passes that model explicitly, and `--provider` and
`--model` on `codeguard eval` override every level for that run:

1. The rule's binding (`provider`, `model`): a per-rule override, for a rule whose eval
   passes on one model only.
2. The project's default, `judge.model` and `judge.provider` in `.codeguard/config.yaml`.
3. The rule package's default, `judge.model` and `judge.provider` in
   `codeguard-package.yaml`: what the package's rules were written and evaluated
   against.

When no level names a model, codeguard runs the provider's CLI with no `--model` flag,
so the CLI's own default judges, as it does for the user. A Bedrock or Vertex AI run
needs a model named by configuration.

The project config is a pydantic-settings model. Its sources, in priority order: values
passed in code, then environment variables, then `.codeguard/config.yaml` (a YAML
source codeguard places below the environment), then field defaults. An environment
variable named after a key overrides the file: with the prefix `CODEGUARD_` and `__`
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
inference profile.

A model is named once, by the id its vendor gives it, and each provider maps that id onto
its own API:

- A Claude model is named by its Anthropic id, the one the `claude` CLI takes:
  `claude-haiku-5-5`. A GPT model is named by its OpenAI id, the one the `codex` CLI
  takes: `gpt-6-luna`. A CLI sends the id as is. The Bedrock provider names it to
  pydantic-ai as the cross-region inference profile `<prefix>.<vendor>.<id>`, the vendor
  `anthropic` for a Claude model and `openai` for a GPT model:
  `us.anthropic.claude-haiku-5-5`, `us.openai.gpt-6-luna`. The prefix is the project's
  `judge.bedrock.inference_prefix` (`us` unless set; pydantic-ai also lists `global`,
  `eu`, `au` and `jp`). A project that must route through an application inference
  profile sets `judge.bedrock.inference_profile` to its ARN, which pydantic-ai sends as
  the request's `modelId` in place of the model name (its `bedrock_inference_profile`
  setting). So `judge: {model: claude-haiku-5-5}` as a package default judges with Haiku
  5.5 on the CLI locally and on Bedrock in CI, with no other change, in a project that
  sets no model of its own.
- A Gemini model is named by its Vertex AI id, `gemini-3.1-pro-preview`, and runs on
  Vertex AI. It needs no `provider`.
- `provider` names where a Claude or GPT model runs: `claude-cli` (the default) or
  `bedrock` for a Claude model, `codex-cli` or `bedrock` for a GPT model. A GPT model
  needs `provider` set: with none, it is a configuration error that says to set it. A
  provider the surface can't use is an error, never a fallback.

A rule package's CI runs its model matrix with `codeguard eval --provider` and
`--model`, today over Gemini on Vertex AI and Claude Haiku 5.5 on Bedrock.

### Testing a rule

- Pattern rules and gates: `codeguard test`, with valid and invalid cases and snapshots.
- Judge rules: `codeguard eval`. Each case is a small fixture repository plus a change,
  with the expected violations. A case passes only when it gets the right verdict at 0.9
  or above on every run. The eval prints the judge's reason for every case, as context
  for fixing the rule's wording; nothing checks it.
- Rule failures: a failing case is fixed in the rule's wording or in the case, never by
  re-running it, never by steering the judge in the prompt, and never by adding the
  case's code to the rule as an example.
- Follow the writing-rules reference's
  [eval case guidance](../skills/writing-rules/references/judge-rules.md#write-a-few-clear-eval-cases).

## Invariants

Every design must satisfy these.

**Single source**

1. Each requirement is written in exactly one place: a pattern rule when it can be
   checked mechanically, otherwise skill prose. Never both, never copied. A pattern rule is
   checked only by code, never by an LLM.
2. Everything the judge enforces is in the skill the writing agent loads. The writing
   agent may get extra guidance the judge doesn't enforce. There is no separate review
   rubric.
3. Each file-to-rule mapping is defined in exactly one place: the bindings.

**The same review locally and in CI**

4. Local and CI reviews run the same engine: the same routing, checks, judge template and
   diagnostic schema.
5. Every judge input is deterministic: the same files and skill version give the same
   prompt on every surface and machine. What the judge reads with its tools comes from the
   same files on every surface. Providers with file-read tracking record those dependencies.
   The verdict itself may vary.
6. The judge sees only what the harness passes it and what it reads with read-only tools
   from the review's files. No user or project config, CLAUDE.md, hooks, plugins or other
   skills reach it.

**Deterministic except where stated**

7. Code decides the candidate rules: bindings map files to rules, a preset list adds
   critical concerns, and triggers remove the rules whose code the change can't reach.
   Change classification may remove a candidate only by deciding the change cannot make it
   fail; a failed or timed-out classification keeps every candidate. Choosing rules that
   no binding maps is out of scope while the writing agent can't load their skills
   before it edits. Code decides each step's prompt.
8. Only three steps call a model: change classification, the judge and verify. Caching,
   recall tests and confidence gating bound their variation. Every other step is
   deterministic.
9. Hook inputs come only from documented host payloads, never from the transcript.

**Prevention before correction**

10. Before an agent edits a file, the file's applicable skill is loaded in that agent's
    context.

**Progress and blocking**

11. An internal error fails loud: a visible message and an error span. It blocks by
    default: a failed judge call takes its rule's severity, and locally the Stop hook
    blocks once, then lets the stop through. A bypass is explicit and per change, never
    the default.
12. Write-time hooks block only for: the applicable skill not loaded, a failed
    deterministic check, or a high-confidence violation.
13. Severity decides blocking: an `error` blocks the Stop hook and CI; `warning`, `info`
    and `hint` never block. A pattern rule's severity is in its YAML; a judge rule's is its
    binding's (default `error`). A project may override a package rule's severity or
    exclude the rule; an override is a bypass, and the Stop hook tells the agent not to use
    one to silence errors. CI never makes fixes.
14. A review checks the change, not the files it touches:
    - A rule runs only when the change could make it fail.
    - A violation is reported only when the changed code is part of it, whether or not
      the base already had it. A changed line that breaks a rule is reported, so code a
      change touches ends up conforming.
    - Untouched code is not reported, even inside the changed function or class.
    - Scope extends up, never sideways. The enclosing function, class and module count
      only for violations the changed code is part of: an added method that gives its
      class a new responsibility is reported, on the added code. Siblings never count:
      other functions, and the other blocks of a statement (an edit to a `try` block
      doesn't make its untouched `except` part of the change). The judge may read them as
      context.
15. The judge reports violations, never fixes. At Stop, the agent's session, which has the
    skill loaded, decides the fix; CI only reports. Skill text states what breaks the
    rule, not how to change the code.

**Scale and cost**

16. Independent concerns are judged in parallel, one request each, on every surface.
    Their diagnostics merge into one result.
17. Every stage records its time and cost. Optimizations wait until metrics show where
    time and cost go.
18. Which judge runs is configuration, never code that knows the surface. Switching
    providers costs one or two configuration values, and the whole system follows.
    codeguard has no built-in model. CI never uses a subscription or a CLI tool: it
    judges through pydantic-ai with the environment's credentials. The `claude` CLI never
    runs against a model in CI; unit tests cover that it is called and its output
    consumed.

**Portability**

19. The framework has no rules built in and depends on no language. Content is
    discovered at runtime.
20. Claude Code and Codex are supported equally, each through its own adapter.
21. An existing tool or host feature is used whenever it satisfies the other invariants.
22. A rule passes whichever model a user picks: a rule package's CI runs every rule eval
    on each supported model, overriding each rule's binding for that run. The bar is 20
    of 20 for a new or changed rule and 3 of 3 otherwise, in CI.

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
  derived from the vendor's id (Judge configuration).
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
