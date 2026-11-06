# codeguard's architecture

This document is an overview of how codeguard works and the invariants its design keeps.
A change to codeguard must keep every invariant here; a change that would break one needs
the maintainers' approval before it is made. [The review pipeline](review-pipeline.md)
and [The judge](judge-design.md) hold the detail.

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
git and pinned to a commit.

Use the writing-rules skill's
[tool-selection guidance](../skills/writing-rules/references/choosing-a-tool.md)
to decide whether a requirement belongs to an existing checker, a pattern rule or a
judge rule. Passing one rule does not excuse violations owned by other checks.

### Components

- **Bindings** map files to a rule by path globs. A binding sets the rule's severity and
  its triggers, and may name its judge provider and model over the project's and the
  package's defaults.
- **The review pipeline** picks the candidate rules, runs the pattern rules, calls the
  judge on the changes its triggers reach and reuses cached verdicts
  ([The review pipeline](review-pipeline.md)).
- **The judge** grades one rule against one file's change, through the `claude` or
  `codex` CLI, Amazon Bedrock or Gemini on Vertex AI ([The judge](judge-design.md)).
- **Host adapters** turn a hook payload into a CLI call, and the CLI's result into a block
  or a pass. The only adapter is for the Stop hook.
- **The CLI** is the core interface: `review` reviews a changeset; `test` runs pattern
  rule and gate tests, with no model; `eval` runs judge rule evals, repeated N times;
  `config` prints a setting. The plugin ships the CLI, and the GitHub Action runs it in
  CI ([CLI](cli.md)).

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
    on each supported model, overriding each rule's binding for that run, to the bar in
    [The bar for a judge rule](testing.md#the-bar-for-a-judge-rule).

