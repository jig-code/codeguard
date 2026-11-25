---
name: writing-rules
description: Writes codeguard rules: decides whether a convention is codeguard's to check, states it as a pattern rule or a judge rule, gates it and writes its cases. Use when someone asks for a codeguard rule, or for codeguard to check a convention, and when adding or changing a codeguard rule, its tests, or its snapshots — any file under .codeguard/ or in a codeguard rule package. Use even if you already know ast-grep; codeguard adds its own layout, scoping and tests.
---

# Writing codeguard rules

A pattern rule is an ast-grep rule that matches code by its syntax. A judge rule is a
convention stated in prose, which a model judges each change against.

Write every part of a rule in plain, clear words that a developer new to the project
understands on the first read, and never in a term you invent.

## Workflow

1. **Pick the tool.** Read `references/choosing-a-tool.md` before writing any rule.
2. **State the convention and why it exists**, as the two sections below say. Then check
   the statement against each bullet under The convention and each check below, and
   rewrite the statement until it meets them all:
   1. Write every relative pronoun that a phrase needs.
   2. Wherever a pronoun could mean more than one noun, write the noun instead.
3. **Gate it**: a pattern rule's match (Pattern rules, below), or a judge rule's
   `triggers` (`references/judge-rules.md`).
4. **Write the cases** (Cases, below).

For a judge rule, also read `references/judge-rules.md` before writing or changing it.
Before writing any rule file, read `references/layout.md`.

## The convention

A rule states one convention, in one declarative sentence, at the level of intent and in
words that don't depend on the language. Each piece of code the rule reads keeps the
convention or breaks it, and the statement alone decides which.

- **What code must never do.** The statement says what code must never do.
- **Once.** The statement says what it forbids once.
- **Nothing about how.** The statement says nothing about how code avoids what it
  forbids.
- **No reason or consequence.** Every clause of the statement describes what the code it
  forbids does. Why the convention exists, and what follows once that code has run,
  belong in the rule's why.
- **Abstract.** The statement states an intent, never a list of code shapes, values or
  names, so it also decides code that no list would name.
- **One convention.** When a request holds more than one convention, write one rule for
  each. Code that the statement doesn't decide goes to a rule of its own or is dropped,
  never kept as an extra clause beside the statement.
- **Scoped to the change.** The statement is decided by the code a change adds or edits
  and the definitions of the names that code uses. Only a convention that keeps
  something unique or consistent across the repository reaches further.
- **Idiomatic code keeps it.** Code written the way the language and its libraries
  intend never breaks the rule. Calling a framework's API is idiomatic; copying the
  framework's shape into the project's own code may not be. A statement that idiomatic
  code breaks is restated, not given an exception.
- **Decided by its wording, never by examples.** A case that the statement decides
  wrongly, or on the wrong ground, shows the statement is unclear: reword the statement
  until it decides the case.
- **Never contradicts another rule.** Code that another rule in the project or package
  requires never breaks a new rule.
- **Never overlaps another rule.** Code that breaks another rule never also breaks a new
  rule. When it does, move that code's shape to one rule, or merge the two rules.
- **A rule names a specific class, function or file only when its convention is about
  that one.** A rule meant for many classes or functions describes what they share,
  never one of them standing in for the rest.

## Why it exists

Every rule states the harm it prevents, in one or two sentences, so that whoever changes
the code or the design around it can tell whether the rule still holds.

- A judge rule: a `## Why` section in its rule file (`references/judge-rules.md`).
- A pattern rule: `metadata.why` in its rule file.
- Optionally, where the rule comes from: a `Source:` line in the Why section, or
  `metadata.source`. A link to public documentation, or the bug, PR comment or team
  decision behind it.

A gate is a judge rule's trigger, not a rule, and needs no why.

## Pattern rules

- Match a shape only where it breaks the convention, not everywhere it appears.
  `stopBy: end` on `has` or `inside` searches every descendant or ancestor; in a
  positive match, use it only when the shape breaks the convention in every position.
- Put the reason and the fix in the rule's `note`, not in comments in the rule's file.
  codeguard prints the note under the diagnostic, so it is what the blocked agent reads.
- Scope a rule with a binding, `bindings/<id>.yaml` with `rule`, `paths` and
  `exclude_paths`, never with ast-grep's `files` or `ignores`, so a project can change
  the scope. The exception is a rule whose convention is about which file code belongs
  in.
- When syntax decides only some of the shapes that break a convention, write a pattern
  rule for those shapes and a judge rule gated on every shape. No judge rule runs on a
  file with an `error` diagnostic, so the two report the same code only if the pattern
  rule is a `warning`.

## Cases

- Use made-up code and names, so a case shows the pattern rather than one class in the
  codebase. A public rule package never holds code copied from a private repository.
- Give idiomatic code a `valid` case beside the `invalid` one.
- A pattern rule: one `valid` or `invalid` case per branch, so deleting a branch fails a
  case, with a comment above each case naming its branch. Give each matched shape a
  `valid` case where the convention allows it, if it has such a position, so a rule that
  matches too widely fails a case.
- A judge rule: a few clear `invalid` and `valid` cases and a `skipped` case outside
  the gate (`references/judge-rules.md`).
- A case's name gives only the situation it tests, unique per file. The expected outcome
  is stated once: in a rule eval case's `expected_output`, or by the `valid` or `invalid`
  list a pattern rule or gate test case sits in.
- Two cases that break or keep the convention on the same ground are one case, however
  their syntax or names differ: keep the clearer one. Two `valid` cases differ when
  their code keeps the convention in different situations, not merely by both not
  breaking it. Before writing a case, say in one sentence what its code does; if another
  case already has that sentence, don't write the case.
- A case breaks the convention in one way at most, the one it tests. Read every other
  line of it as a reviewer would, and rewrite any line that is wrong for another reason,
  so nothing else in the case can decide its outcome.

## Every rule

- Set `severity: error` on a rule that must block; `warning` only reports.
- A finding you think is wrong is fixed in the rule or its cases, never by changing the
  reviewed code to get past it.
- Leave the codebase clean for a new rule: fix each piece of code that breaks it, or put
  an `ast-grep-ignore: <id>` comment on the line above it.
