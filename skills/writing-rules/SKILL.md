---
name: writing-rules
description: Writes codeguard rules: decides whether a convention is codeguard's to check, states it as a pattern rule or a judge rule, gates it and writes its cases. Use when adding or changing a codeguard rule, its tests, or its snapshots — any file under .codeguard/ or in a codeguard rule package. Use even if you already know ast-grep; codeguard adds its own layout, scoping, and test conventions.
---

# Writing codeguard rules

A pattern rule matches code by its syntax. A model judges each change against a judge
rule.

## Workflow

1. **Pick the tool.** Read `references/choosing-a-tool.md` before writing any rule.
2. **State the convention and why it exists**, as the two sections below say. Then reread
   the statement once for each of these bullets under The convention: A statement, never
   a question; What code must never do; Once; Nothing about how; No reason or
   consequence; and Common terms. Reread it once more for each check below. Rewrite the
   statement until it meets them all:
   1. Write every relative pronoun that a phrase needs.
   2. Wherever a pronoun could mean more than one noun, write the noun instead.
   3. Name what code does, never what code leaves out: use no "without" followed by a
      verb, no "fail to", no "skip", and no "leave" with "undone".

   Reread the two sections when two rules, or a rule and its cases, disagree about the
   same code.
3. **Gate it**: a pattern rule's match (Pattern rules, below), or a judge rule's
   `triggers` (`references/judge-rules.md`).
4. **Write the cases** (Cases, below).

For a judge rule, also read `references/judge-rules.md` before writing or changing it.

## The convention

A rule is one convention, stated as one declarative sentence at the level of intent and
in words that don't depend on the language. Each piece of code the rule reads either
keeps the convention or breaks it: that is the rule's one yes/no test. The rule is that
statement and why it exists, and nothing else. The judge treats any other text, even a
clause in the statement, as a separate test. Code can pass that test and still break the
statement. The statement alone decides each piece of code; the judge reads the statement
as a reviewer would, and says on what ground the code keeps or breaks it.

- **A statement, never a question.** The judge decides whether code breaks the
  convention it is given; a question in its place leaves the judge to infer which
  answer is the violation.
- **What code must never do.** The statement says what code must never do. The judge
  looks for code that breaks the rule, so the statement names that code.
- **Once.** The statement says what it forbids once. A second statement of the same
  thing is a test of its own, and it can drift from the first.
- **Nothing about how.** The statement says nothing about how code avoids what that code
  must never do.
- **No reason or consequence.** The statement gives no reason for the convention and no
  consequence of breaking it.
- **Abstract.** A rule states an intent, never a list of code shapes, values or names: a
  shape nobody listed is still decided by its statement. Rules that each police one code
  shape contradict each other and fail idiomatic code.
- **One convention.** A rule stating several conventions under one intent is several
  rules. Split it into one rule per convention, or find the one statement they share.
  A shape the statement doesn't decide is dropped from the rule, or moved to a rule of
  its own; it is never kept as an extra violation beside the statement.
- **Common terms.** The statement uses only common terms, never a term the author
  invents: the judge reads an invented term as loosely as a person does.
- **Scoped to the change.** A rule and its cases ask for only as much as decides pass or
  fail: the code the change adds or edits, and the definitions of the names it uses. A
  judge that has to read the rest of the repository to decide is slower, costs more, and
  wavers. Only a rule that keeps something unique or consistent across the repository
  (one home for a job, one word for one operation) searches beyond that, and it names
  the one search it needs.
- **Idiomatic code never breaks it.** Code written the way the language and its
  libraries intend is never a violation. A bad pattern isn't idiomatic just because a
  framework uses it, though: calling the framework's API is fine, while copying its
  shape into the project's own code may not be. A statement that flags idiomatic code
  is restated so it doesn't; it isn't given an exception for that code.
- **Decided by its wording, never by examples.** A case that the statement decides
  wrongly, or on the wrong ground, shows the statement is unclear: reword it so the
  statement decides the case. An example would only make the judge match code to it, and
  the next case fails the same way.
- **Never contradicts another rule.** A new rule never flags what another rule in the
  project or package requires.
- **Never overlaps another rule.** A new rule never flags code that another rule already
  flags. When two rules flag the same code, move that code's shape to one rule, or merge
  the two rules.
- **A rule names a specific class, function or file only when its convention is about
  that one.** A rule meant for many classes or functions matches what they share, never
  one of them standing in for the rest.

## Why it exists

Every rule states the harm it prevents, in one or two sentences, so it can be reviewed
when the code or the design around it changes. A rule nobody can trace to a reason can
only be kept or dropped blind.

- A judge rule: a `## Why` section in its skill (`references/judge-rules.md`).
- A pattern rule: `metadata.why` in its rule file.
- Optionally, where the rule comes from: a `Source:` line in the Why section, or
  `metadata.source`. A link to public documentation, or the bug, PR comment or team
  decision behind it.

A gate is a judge rule's trigger, not a rule, and needs no why.

## Layout

- Pattern rule: `.codeguard/rules/pattern/<id>.yml`; its tests:
  `.codeguard/rule-tests/<id>-test.yml`, never under the rules directory (every YAML file
  there loads as a rule).
- Judge rule: the skill `.codeguard/skills/<id>/SKILL.md`, the binding
  `.codeguard/bindings/<id>.yaml` and the rule eval `.codeguard/rule-evals/<id>.yaml`.
  A judge rule isn't written until all three exist; write the binding and the rule eval
  in the same pass as the skill, never leave them for later.
  - The binding sets `skill` (the skill's directory), `paths` (globs of the files the
    rule reviews) and `triggers` (the change kinds or gates that call the judge, never
    `any`, `code`, `function-body` or `function-signature`).
  - The rule eval holds `cases`, each with a `name`, `inputs` (`file`, the edited file's
    path; `before`, the file before the edit, left out for a new file; `after`, the
    file after it) and `expected_output` (`outcome`: `invalid`, `valid` or `skipped`).
- Gate: `.codeguard/gates/<id>.yml`, an ast-grep rule tested by
  `.codeguard/rule-tests/<id>-test.yml`.
- In a rule package (a repo with `codeguard-package.yaml`), the same layout sits under
  each ruleset's directory instead of `.codeguard/`.
- A judge rule whose convention holds in several languages is one rule: its binding's
  paths name each language, and its eval has cases in each (codeguard's
  `docs/rule-formats.md`, A rule in several languages). The skill is written in no
  language's names, syntax or libraries, and gets no supplement per language. Never copy
  a convention into a rule per language. A pattern rule matches one language.
- Before writing a rule, check the rulesets the project opts into in
  `.codeguard/config.yaml`. To change a packaged rule for this project, override or
  exclude it there; don't copy it into `.codeguard/`.

codeguard's `docs/rule-formats.md` has the binding and rule eval formats.

## Pattern rules

- Match the shape only where it breaks the convention, not everywhere it appears.
  `stopBy: end` on `has` or `inside` searches every descendant or ancestor; in a
  positive match, use it only when the shape breaks the convention in every position.
- Put the reason and the fix in the rule's `note`, not in comments in the rule's file.
  codeguard prints the note under the diagnostic, so it is what the blocked agent reads.
- Scope a rule with a binding, `bindings/<id>.yaml` with `rule`, `paths` and
  `exclude_paths`, never with ast-grep's `files` or `ignores`, so a project can change
  the scope. The exception is a file name that is the convention itself.
- When syntax decides only some shapes a violation takes, write a pattern rule for those
  shapes and a judge rule gated on every shape. No judge rule runs on a file with an
  `error` diagnostic, so the two report the same code only if the pattern rule is a
  `warning`.

## Cases

- Use made-up code and names, so a case shows the pattern rather than
  one class in the codebase. A public rule package never holds code copied from a
  private repository.
- Give idiomatic code a `valid` case beside the `invalid` one.
- A pattern rule: one `valid` or `invalid` case per branch, so deleting a branch fails a
  case, with a comment above each case naming its branch. Give each matched shape a
  `valid` case where the convention allows it, if it has such a position, so a rule that
  matches too widely fails a case.
- A judge rule: a few clear `invalid` and `valid` cases and a `skipped` case outside
  the gate (`references/judge-rules.md`).
- A case's name gives only the situation it tests, unique per file. The verdict is
  stated once: in a rule eval case's expected outcome, or by the `valid` or `invalid`
  list a pattern rule or gate test case sits in.
- Two cases that break or keep the convention on the same ground are one case, however
  their syntax or names differ: keep the clearer one. Two `valid` cases differ when
  their code keeps the convention in different situations, not merely by both lacking
  the violation. Before writing a case, say in one sentence what its code does or fails
  to do; if another case already has that sentence, don't write the case.
- A case holds one defect at most, the one it tests. Read every other line of it as a
  reviewer would, and rewrite any line that is wrong for another reason, so nothing
  else in the case can be the ground of a verdict.

## Every rule

- Set `severity: error` on a rule that must block; `warning` only reports.
- A finding you think is wrong is fixed in the rule or its cases, never by changing the
  reviewed code to get past it.
- Leave the codebase clean for a new rule: fix each existing violation, or put an
  `ast-grep-ignore: <id>` comment on the line above it.
