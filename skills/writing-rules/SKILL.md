---
name: writing-rules
description: Use when adding or changing a codeguard rule, its tests, or its snapshots — any file under .codeguard/ or in a codeguard rule package. Use even if you already know ast-grep; codeguard adds its own layout, scoping, and test conventions.
---

# Writing codeguard rules

codeguard checks the changed lines of each changed file against the project's rules:
pattern rules (ast-grep) and judge rules (a skill a model judges the change against). An
`error` diagnostic blocks the agent's Stop and fails CI. Each principle here corrected a
rule that misjudged code.

## Workflow

1. **Decide whether it's a codeguard rule**, and which kind. Read
   `references/choosing-a-tool.md` before writing any rule. Write no rule, even when
   asked for one, for a convention a deterministic check can decide exactly: a linter,
   a type checker, an import linter, a language server or, when no tool has the check,
   a project script run in CI. That check is the right one whether or not the project
   runs it or has it turned on. Tell the user which kind of check can decide it instead.
2. **State the convention and why it exists**, as the two sections below say. Reread
   them when two rules, or a rule and its cases, disagree about the same code.
3. **Gate it**: a pattern rule's match (Pattern rules, below), or a judge rule's
   `triggers` (`references/judge-rules.md`).
4. **Write the cases** (Cases, below).
5. **Verify** (Verify, below).

For a judge rule, also read `references/judge-rules.md` and
`references/judge-rule-files.md` before writing or changing it, and read
`references/judge-rules.md` whenever its eval fails, flips between runs or reports a
warning. For examples in the
project's language, read `references/python.md`, `references/typescript.md` or
`references/ruby.md`.

## The convention

A rule is one convention, stated as one declarative sentence at the level of intent, in
words that don't depend on the language. Each piece of code the rule reads either keeps
the statement or breaks it: that is the rule's one yes/no test. The rule's forms (the
shapes the violation takes in the language and its libraries) illustrate the statement
on both sides: the statement alone decides each form, and no form defines its own
violation.

- **A statement, never a question.** The judge decides whether code breaks the
  convention it is given; a question in its place leaves the judge to infer which
  answer is the violation.
- **Abstract.** A rule states an intent, never a list of code shapes, values or names: a
  shape nobody listed is still decided by its statement. Rules that each police one code
  shape contradict each other and fail idiomatic code.
- **One convention.** A rule stating several conventions under one intent, or whose
  statement only points at its forms ("code breaks this when it takes a form below"), is
  several rules. Split it into one rule per convention, or find the one statement the
  forms share and drop the forms it doesn't decide.
- **Plain language.** Write it the way a reviewer would say it in a code review. No
  invented terms: if the rule needs a word nobody uses, it isn't clear yet. A judge
  reads an unfamiliar term as loosely as a person does.
- **Scoped to the change.** A rule and its cases ask for only as much as decides pass or
  fail: the code the change adds or edits, and the definitions of the names it uses. A
  judge that has to read the rest of the repository to decide is slower, costs more, and
  wavers. Only a rule that keeps something unique or consistent across the repository
  (one home for a job, one word for one operation) searches beyond that, and it names
  the one search it needs.
- **Idiomatic code never breaks it.** Code written the way the language and its
  libraries intend is never a violation. A bad pattern isn't idiomatic just because a
  framework uses it, though: calling the framework's API is fine, while copying its
  shape into the project's own code may not be.
- **Each code shape breaks at most one rule.** When two rules contradict each other (one
  flags what the other requires) or overlap (both flag the same code), settle it before
  either ships: move the shape to one rule, or merge them.
- **Match a code pattern, never a named class, function or file.**

## Why it exists

Every rule states the harm it prevents, in one or two sentences, so it can be reviewed
when the code or the design around it changes. A rule nobody can trace to a reason can
only be kept or dropped blind.

- A judge rule: a `## Why` section in its skill (`references/judge-rules.md`).
- A pattern rule: `metadata.why` in its rule file. codeguard doesn't print it; `note`
  stays what the blocked agent reads.
- Optionally, where the rule comes from: a `Source:` line in the Why section, or
  `metadata.source`. A link to public documentation, or the bug, PR comment or team
  decision behind it.

A gate is a judge rule's trigger, not a rule, and needs no why. `codeguard test` reports
a rule without one.

## Layout

- Pattern rule: `.codeguard/rules/pattern/<id>.yml`; its tests:
  `.codeguard/rule-tests/<id>-test.yml`, never under the rules directory (every YAML file
  there loads as a rule).
- Judge rule: the skill `.codeguard/skills/<id>/SKILL.md`, the binding
  `.codeguard/bindings/<id>.yaml` (`skill`, `paths`, `triggers`), and the rule eval
  `.codeguard/rule-evals/<id>.yaml`.
- Gate: `.codeguard/gates/<id>.yml`, an ast-grep rule tested by
  `.codeguard/rule-tests/<id>-test.yml`.
- In a rule package (a repo with `codeguard-package.yaml`), the same layout sits under
  each ruleset's directory instead of `.codeguard/`.
- A judge rule whose convention holds in several languages is one rule: its binding's
  paths name each language, and each language's forms go in a supplement beside the
  skill (codeguard's README, A rule in several languages). Never copy a convention into
  a rule per language. A pattern rule matches one language.
- Before writing a rule, check the rulesets the project opts into in
  `.codeguard/config.yaml`. To change a packaged rule for this project, override or
  exclude it there; don't copy it into `.codeguard/`.

`references/judge-rule-files.md` has the judge rule's file formats; codeguard's README
has the rest.

## Pattern rules

- Match the construct only where it breaks the convention: a `len()` compared with a
  literal, not a `len()` inside a slice. `stopBy: end` on `has` or `inside` searches every
  descendant or ancestor; in a positive match, use it only when the construct breaks the
  convention in every position.
- Put the reason and the fix in the rule's `note`. codeguard prints it under the
  diagnostic, so it is what the blocked agent reads (no comments in rule files).
- Scope a rule with a binding, `bindings/<id>.yaml` with `rule`, `paths` and
  `exclude_paths`, never with ast-grep's `files` or `ignores`, so a project can change
  the scope. The exception is a file name that is the convention itself (`__all__` only
  in `__init__.py`).
- When syntax decides only some forms of a convention, write a pattern rule for those
  forms and a judge rule gated on every form. No judge rule runs on a file with an
  `error` diagnostic, so the two report the same code only if the pattern rule is a
  `warning`.

## Cases

- Use made-up code and names (`ExampleModel`), so a case shows the pattern rather than
  one class in the codebase. A public rule package never holds code copied from a
  private repository.
- Name every case for why its code breaks or keeps the convention, not only for what
  the code does: "a getter that saves surprises a caller who only reads", not "calls save in
  get_order"; and for another form of the same violation, "an is_ check that sends an
  email has a side effect its name hides", not "sends an email in is_overdue".
- Give the idiomatic form a `valid` case beside the `invalid` one. A judge rule's `valid`
  case is an edit its triggers reach, so the judge sees it and passes it; an edit
  outside the triggers is a `skipped` case, which never reaches the judge.
- A pattern rule: one `valid` or `invalid` case per branch, so deleting a branch fails a
  case, with a comment above each case naming its branch. Give each matched construct a
  `valid` case where the convention allows it, if it has such a position, so a rule that
  matches too widely fails a case.
- A judge rule: `invalid`, `valid` and `skipped` cases at the boundary of its convention
  (`references/judge-rules.md`).

## Every rule

- Set `severity: error` on a rule that must block; `warning` only reports.
- A finding you think is wrong is fixed in the rule or its cases, never by changing the
  reviewed code to get past it.
- Leave the codebase clean for a new rule: fix each existing violation, or put an
  `ast-grep-ignore: <id>` comment on the line above it.

## Verify

A rule is proven accurate only by its own cases, run through codeguard. Running it over
other code finds code to fix, not evidence that the rule is right.

```sh
codeguard test                 # rule tests and eval triggers; --update-all regenerates snapshots
codeguard eval --rule <id> --repeat <n>  # a judge rule's cases, each judged n times; calls the model
codeguard review --all --dry-run  # existing violations of pattern rules; calls no model
```

Never run `codeguard review --all` without `--dry-run`: it judges every file against
every judge rule. codeguard's README has every command's options.
