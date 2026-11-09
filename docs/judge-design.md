# The judge

The judge grades one rule against one file's change. [codeguard's
architecture](architecture.md) has the overview and the invariants it keeps; [Choose a
judge](judges.md) says how to set each provider up.

## What the judge does

The judge returns violations, never fixes. The providers are the `claude` CLI in safe
mode, the `codex` CLI in a read-only sandbox, and Gemini on Vertex AI and Claude or GPT on
Amazon Bedrock (both pydantic-ai, with equivalent tools).

- Its input: the judge template, which holds the instructions; the skill text; the
  `changes` element, an excerpt of the changed code with `+`, space and `-` marks and the
  file's own line numbers; and read-only tools (Read, Grep, Glob) over the repository at
  the change.
- What it reads: the prompt holds what the judge will certainly need. The judge decides
  from the rule what else to read, and reads it with its tools. The prompt never says
  what to read or when. When a model fails to read what an obvious case needs, that is a
  finding about the model, not a reason to change the prompt.
- What it sees: nothing else. No CLAUDE.md, hooks, plugins or other skills reach it.
- Its output: a reason for its verdict, pass or fail, saying what in the changed code
  keeps the rule or breaks it, as context for whoever troubleshoots the verdict;
  and violations, each with a file, line, message and confidence (1.0, 0.9, 0.7 or 0.5).
  A violation is reported only where the changed code is part of it.

## How the model is chosen

A judge rule is judged with its binding's provider and model, the ones its rule eval
passed on; a binding that sets neither is judged with `claude-sonnet-5-5` through the
`claude` CLI. A project can't switch a rule to another model
([No setting on purpose](configuration.md#no-setting-on-purpose)).
`codeguard eval --provider` and `--model` judge an eval with another model, and change
nothing a review judges with.

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
- **Isolation (#6).** The Claude provider runs `claude --safe-mode`, which loads no
  CLAUDE.md, skills, plugins, hooks, MCP servers or memory. Its tools are read-only and
  rooted at the repository. It runs no subagents. The Codex provider runs `codex exec`
  in a read-only sandbox with project instructions, hooks, plugins, memories and web
  search off. The Gemini and Bedrock providers have equivalent read-only tools.
- **Model.** A full model id, never an alias, so a model change is visible to the cache.
- **Output.** Validated against the verdict schema; output that fails validation fails
  the run loudly.
- **Confidence scale**, stated in the verdict schema: 1.0 when the judge is certain the
  code breaks the rule and nothing in the working directory points to an allowed
  exception; 0.9 when the code breaks the rule as written but the verdict rests on a
  reading of the rule's terms a reviewer could contest; 0.7 when something in the working
  directory points to an allowed exception; 0.5 when a violation is as likely as not;
  below 0.5, not reported. The scale never rewards resemblance to an example: rules hold
  none.
- **Determinism (#5).** Claude Code adds the date, the account and the working directory
  to the message. Those are the only inputs codeguard doesn't control.

## How each provider runs

The `codex` CLI judge runs `codex exec` with ephemeral sessions and the shared verdict
schema, and uses Codex's native repository tools in the read-only sandbox. Temporary
files hold the shared judge instructions, verdict schema and final response; they are
removed after each call. The provider uses `high` reasoning effort and the review
deadline. Authentication failures, capacity errors and other process errors fail
immediately, without retries or a separate per-call time limit. Codex uses the verdict
cache keyed on the judge inputs and reviewed source. Native events do not provide
complete file-read tracking, so Codex does not populate `loaded_files` for context-file
invalidation. Concurrency follows the CLI limit, one call per CPU.

Gemini reads the working directory through read-only `read_file`, `grep` and `glob`
tools, limited to the repository, thinks at the `LOW` level, and returns its verdict as
structured output with the same verdict schema as Claude. A judgement that makes 10
requests without a verdict is reported as not judged. Bedrock runs through the same
tools.

Gemini's pay-as-you-go capacity is shared and limited by tokens per minute, so the
gemini provider makes 2 calls at once (`judge.calls_at_once`). Each provider has its own
limit, so Claude and Gemini rules in one review don't wait on each other. A request that
Gemini turns away (408, 429 or a 5xx) or whose connection breaks is sent again for about
15 seconds, and then the rule is reported as not judged.
