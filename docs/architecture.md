# codeguard's architecture

This document describes how codeguard works and the invariants its design keeps. A change
to codeguard must keep every invariant here; a change that would break one needs the
maintainers' approval before it is made.

## How codeguard works

### Purpose

codeguard makes coding agents (Claude Code and Codex) follow a project's coding
conventions. Each convention is written once and applies wherever code is written or
reviewed: while the agent works, and in CI.

- Prevention: the agent loads the skill for a file before it edits that file.
- Correction: every change is reviewed by deterministic checks and an LLM judge. The
  review runs when the agent stops and in CI, and errors block.

codeguard has no conventions and no languages built in. Projects and rule packages supply
all of them.

### Rules

Each convention is checked by exactly one rule, of one of two kinds:

- A pattern rule is an ast-grep rule, for a convention that can be checked mechanically.
  Only code checks it, never a model. Its note explains why the convention exists and
  how to fix a violation.
- A judge rule is a skill (`SKILL.md`), for a convention that needs judgment. The skill
  body is the convention. The writing agent loads that text and the judge grades against
  the same text. There is no separate rubric.

Rules live in a project's `.codeguard/` directory or come from rule packages fetched from
git and pinned to a tag. Every surface reviews with the same rules.

### Components

**Bindings** map files to a rule by path globs. A binding sets the rule's severity, its
triggers, and its judge provider and model.

**Triggers and gates** decide whether a judge rule runs on a change at all. A judge rule
is called only when the change touches one of its triggers. A trigger is a change kind
(`import`, `function-body`, …) or a gate. A gate is an ast-grep rule that matches where a
violation could appear.

**The review pipeline** is the same code on every surface (the Stop hook, CI and
`codeguard review`):

1. Take the changeset.
2. Bindings and triggers pick the candidate rules.
3. Pattern rules run. A file with a blocking pattern diagnostic skips the judge.
4. Classify (planned): a model drops the rules the change can't make fail.
5. The judge makes one call per rule and file, in parallel.
6. Verify (gated): a second model call confirms each violation.
7. The confidence threshold applies: a violation below 0.9 is reported as a warning,
   never dropped.
8. The results merge into one.

**The judge** grades one rule against one file's change and returns violations, never
fixes. The providers are Claude (the `claude` CLI in safe mode) and Gemini (pydantic-ai,
with equivalent tools).

- Its input: the judge template, which holds the instructions; the skill text; the
  `changes` element, an excerpt of the changed code with `+`, space and `-` marks and the
  file's own line numbers; and read-only tools (Read, Grep, Glob) over the repository at
  the change.
- What it reads: the prompt holds what the judge will certainly need. The judge decides
  from the rule what else to read, and reads it with its tools. The prompt never says
  what to read or when. When a model fails to read what an obvious case needs, that is a
  finding about the model, not a reason to change the prompt.
- What it sees: nothing else. No CLAUDE.md, hooks, plugins or other skills reach it.
- Its output: violations, each with a file, line, message and confidence (1.0, 0.9, 0.7
  or 0.5). A violation is reported only where the changed code is part of it.

**The verdict cache** stores verdicts keyed on the template, model, skill, path, changed
code and whole file. Each verdict records the files the judge read, and is reused only
while all of them are unchanged. Evals and CI never use the cache.

**Host adapters** turn a hook payload into a CLI call, and the CLI's result into a block
or a pass. The only adapter is for the Stop hook. It blocks once on the same errors, then
lets the stop through. Planned: a pre-edit hook that denies an edit until the file's
skill is loaded.

**The CLI** is the core interface: `review` reviews a changeset; `test` runs pattern rule
and gate tests, with no model; `eval` runs judge rule evals, repeated N times; `config`
prints a setting. The plugin ships the CLI, and the GitHub Action runs it in CI.

### Testing a rule

- Pattern rules and gates: `codeguard test`, with valid and invalid cases and snapshots.
- Judge rules: `codeguard eval`. Each case is a small fixture repository plus a change,
  with the expected violations. A case passes only when it gets the right verdict at 0.9
  or above on every run.
- Rule failures: a failing case is fixed in the rule's wording or in the case, never by
  re-running it and never by steering the judge in the prompt.

## Invariants

Every design must satisfy these. Each number is a stable identifier that other docs and
the code refer to.

**Single source**

1. Each convention is written in exactly one place: a pattern rule when it can be checked
   mechanically, otherwise skill prose. Never both, never copied. A pattern rule is
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
   same files on every surface, and the verdict records it. The verdict itself may vary,
   within the bounds #8 sets.
6. The judge sees only what the harness passes it and what it reads with read-only tools
   from the review's files. No user or project config, CLAUDE.md, hooks, plugins or other
   skills reach it.

**Deterministic except where stated**

7. Code decides the candidate rules: bindings map files to rules, a preset list adds
   critical concerns, and triggers remove the rules whose code the change can't reach.
   Change classification may remove a candidate only by deciding the change cannot make it
   fail; a failed or timed-out classification keeps every candidate. Choosing rules that
   no binding maps is out of scope until it can satisfy #2. Code decides each step's
   prompt.
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
12. Write-time hooks block only for: the applicable skill not loaded (#10), a failed
    deterministic check, or a high-confidence violation.
13. Severity decides blocking: an `error` blocks the Stop hook and CI; `warning`, `info`
    and `hint` never block. A pattern rule's severity is in its YAML; a judge rule's is its
    binding's (default `error`). A project may override a package rule's severity or
    exclude the rule; an override is a bypass, and the Stop hook tells the agent not to use
    one to silence errors. CI never makes fixes.

<!-- A new list, so Markdown keeps the number 20. -->

20. A review checks the change, not the files it touches:
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
21. The judge reports violations, never fixes. At Stop, the agent's session, which has the
    skill loaded, decides the fix; CI only reports. Skill text states what breaks the
    convention, not how to change the code.

**Scale and cost**

14. Independent concerns are judged in parallel, one request each, on every surface.
    Their diagnostics merge into one result.
15. Every stage records its time and cost. Optimizations wait until metrics show where
    time and cost go.
16. Local judging can use a Claude subscription. CI authentication comes from the
    environment.

**Portability**

17. The framework has no conventions built in and depends on no language. Content is
    discovered at runtime.
18. Claude Code and Codex are supported equally, each through its own adapter.
19. An existing tool or host feature is used whenever it satisfies the other invariants.

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
  the convention needs more.
- **Isolation (#6).** The Claude provider runs `claude --safe-mode`, which loads no
  CLAUDE.md, skills, plugins, hooks, MCP servers or memory. Its tools are read-only and
  rooted at the repository. It runs no subagents. The Gemini provider has equivalent
  read-only tools.
- **Model.** A full model id, never an alias, so a model change is visible to the cache.
- **Output.** Validated against the verdict schema; output that fails validation fails
  the run loudly.
- **Confidence scale**, stated in the template: 1.0 when the code matches a case or
  example the convention describes; 0.9 when it breaks the convention as written; 0.7
  when something points to an allowed exception; 0.5 when a violation is as likely as
  not; below 0.5, not reported.
- **Determinism (#5).** Claude Code adds the date, the account and the working directory
  to the message. Those are the only inputs codeguard doesn't control.
