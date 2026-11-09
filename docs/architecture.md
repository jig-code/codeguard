# codeguard's architecture

This document says why codeguard works as it does and the invariants its design keeps. A
change to codeguard must keep every invariant here; a change that would break one needs
the maintainers' approval before it is made. How each part works is in its code.

## How codeguard works

### Purpose

codeguard raises the floor of the quality of code that a coding agent (Claude Code or
Codex) writes on its own. It does that by defining rules the agent follows in its
development loop, and by reviewing every change against those rules when the agent stops
and in CI. Rules cover architecture and design as well as code-level practice. Each rule
is defined once and applies wherever code is written or reviewed.

- Prevention: the agent loads the skill for a file before it edits that file.
- Correction: every change is reviewed by deterministic checks and an LLM judge. The
  review runs when the agent stops and in CI, and errors block.

codeguard has no rules and no languages built in. Projects and rule packages supply all
of them.

### Rules

A rule states one requirement on code and why it matters. Each requirement is checked
by exactly one rule, of one of two kinds:

- A pattern rule is an ast-grep rule, for a requirement that can be checked mechanically.
  Only code checks it, never a model. Its note explains why the requirement exists and
  how to fix a violation.
- A judge rule is a skill (`SKILL.md`), for a requirement that needs judgment. The skill
  states the requirement and why it matters. The writing agent loads that text and the
  judge grades against the same text. There is no separate rubric.

Rules live in a project's `.codeguard/` directory or come from rule packages fetched from
git and pinned to a tag. Every surface reviews with the same rules.

Use the writing-rules skill's
[tool-selection guidance](../skills/writing-rules/references/choosing-a-tool.md)
to decide whether a requirement belongs to an existing checker, a pattern rule or a
judge rule. Passing one rule does not excuse violations owned by other checks.

### Components

**Bindings** map files to a rule by path globs. A binding sets the rule's severity, its
triggers, and its judge provider and model.

**The review pipeline** ([`review/review.py`](../src/codeguard/review/review.py)) is the
same code on every surface, so a commit gets the same review at the agent's Stop, in CI
and from `codeguard review` (#4). Triggers and gates run first and cheaply, so the judge,
the costly step, is called only for a rule the change could make fail (#20). Pattern
rules run before the judge, and a file with a blocking pattern diagnostic skips it,
because that file has to change anyway.

**The judge** grades one rule against one file's change, through the `claude` or `codex`
CLI, Gemini on Vertex AI or Amazon Bedrock. Its instructions are
[`review/judge.md`](../src/codeguard/review/judge.md). It gets the change as git's
unified diff with function context, not a format of codeguard's own: models already read
it, and its hunk headers mark every line it leaves out.

- The prompt holds only what the judge will certainly have to read; the judge decides
  from the rule what else to read, and reads it with its tools. The prompt never says
  what to read or when, so a rule's verdict rests on the rule's text alone. When a model
  fails to read what an obvious case needs, that is a finding about the model, not a
  reason to change the prompt.
- Each provider runs isolated (#6): no user or project config, instructions, hooks,
  plugins, memory or other skills reach it, so a verdict depends only on the rule and the
  repository.
- The judge reports violations, never fixes (#21), with a reason for its verdict as
  context for whoever troubleshoots it, and a confidence on a fixed scale stated in the
  verdict schema. The scale never rewards resemblance to an example, since rules hold
  none.
- Output that fails the verdict schema fails the run loudly (#11).
- A model is named by its full id, never an alias, so a model change is visible to the
  verdict cache.

**The verdict cache** ([`review/cached_judge.py`](../src/codeguard/review/cached_judge.py))
reuses a verdict until something the judge's answer depends on changes, so an agent that
stops again without changing a file doesn't pay for the same judgement twice. Evals and
CI never use it: an eval tests the rule, and CI judges a commit fresh.

**Host adapters** turn a hook payload into a CLI call, and the CLI's result into a block
or a pass. The only adapter is for the Stop hook, which blocks every time the agent stops
while errors remain.

**The CLI** is the core interface: `review` reviews a changeset; `test` runs pattern rule
and gate tests, with no model; `eval` runs judge rule evals, repeated N times; `config`
prints a setting. The plugin ships the CLI, and the GitHub Action runs it in CI.

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
  [eval case guidance](../skills/writing-rules/references/judge-rules.md#write-a-few-clear-eval-cases),
  and [docs/testing.md](testing.md) for a fixture that holds a pre-existing violation to
  test review scope.

## Invariants

Every design must satisfy these. Each number is a stable identifier that other docs and
the code refer to.

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
   The verdict itself may vary,
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

**Progress and blocking**

11. An internal error fails loud: a visible message and an error span. A failed judge
    call takes its rule's severity. Locally, it goes to the developer and never blocks the
    agent, which can't fix it; a rule's error still blocks every stop until it is fixed. In
    CI, a failed judge call fails the review unless the PR's label bypasses it: a bypass is
    explicit and per change, never the default.
12. Write-time hooks block only for a failed deterministic check or a high-confidence
    violation.
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
21. The judge reports violations, never fixes. At Stop, the agent's session decides the
    fix; CI only reports. Skill text states what breaks the rule, not how to change the
    code.

**Scale and cost**

14. Independent concerns are judged in parallel, one request each, on every surface.
    Their diagnostics merge into one result.
15. Every stage records its time and cost. Optimizations wait until metrics show where
    time and cost go.
16. Local judging can use a Claude subscription. CI authentication comes from the
    environment.

**Portability**

17. The framework has no rules built in and depends on no language. Content is
    discovered at runtime.
18. Claude Code and Codex are supported equally, each through its own adapter.
19. An existing tool or host feature is used whenever it satisfies the other invariants.
