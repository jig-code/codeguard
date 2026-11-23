---
name: writing-rules
description: Writes codeguard rules: decides whether a convention is codeguard's to check, states it as a pattern rule or a judge rule, gates it and writes its cases. Use when adding or changing a codeguard rule, its tests, or its snapshots — any file under .codeguard/ or in a codeguard rule package. Use even if you already know ast-grep; codeguard adds its own layout, scoping, and test conventions.
---

# Writing codeguard rules

A pattern rule is an ast-grep rule that matches code by its syntax. A judge rule is a
convention that a model judges each change against.

## Workflow

1. **Pick the tool.** Read `references/choosing-a-tool.md` before writing any rule.
2. **State the convention and why it exists**, as the two sections below say. Then check
   the statement against each bullet under The convention and each check below, and
   rewrite the statement until it meets them all:
   1. Write out every relative pronoun, so it's clear which noun each phrase describes.
   2. Use the noun instead of a pronoun that could mean more than one thing.
   3. Name an action the code takes, never one it skips: a skipped action isn't on any
      line a change touches.

   Reread the two sections when two rules, or a rule and its cases, disagree about the
   same code.
3. **Gate it**: a pattern rule's match (Pattern rules, below), or a judge rule's
   `triggers` (`references/judge-rules.md`).
4. **Write the cases** (Cases, below).

For a judge rule, also read `references/judge-rules.md` before writing or changing it.
Before writing any rule file, read `references/layout.md`.

## The convention

A rule is one convention, stated as one sentence in words that don't depend on the
language. Each piece of code the rule reads either keeps it or breaks it. The rule holds
that statement and why it exists, and nothing else: any other text is a second test,
which code can pass while breaking the statement.

- **Write a statement, not a question or a command.** A question doesn't say which answer
  breaks the rule, and a command gives an order instead of describing code.
- **Write a negative sentence**, so each piece of code either does what it forbids or
  doesn't.
- **Say it once.** Saying the same thing twice adds a second test.
- **Don't say how to comply.** Code that complies a different way would break that part.
- **Leave out why the rule exists and what goes wrong when it's broken.** Both go in the
  rule's why.
- **Forbid one thing, never a list.** Anything left off a list is left undecided.
- **Write one rule per convention.** Something the statement doesn't cover gets its own
  rule; it isn't added to this one.
- **Use common words.** A made-up term means whatever the reader guesses it means.
- **Make the rule decidable from the changed code and the code it uses.** Reading the rest
  of the repository makes each check slower and less reliable.
- **If the rule keeps something unique or consistent across the repository, name the one
  search it needs.**
- **Code written the way its language and libraries intend never breaks the rule.** If it
  does, reword the statement rather than adding an exception.
- **Fix a wrong verdict by rewording.** An example or an exception fixes only that one
  case.
- **Don't contradict or repeat another rule.** Never forbid what another rule requires or
  already forbids.
- **Name a specific class, function or file only when the rule is about that one.**
  Otherwise, describe what the group has in common.

## Why it exists

Every rule states the harm it prevents, in one or two sentences, so it can be reviewed
when the code or the design around it changes. A rule nobody can trace to a reason can
only be kept or dropped blind.

- A judge rule: a `## Why` section in its rule file (`references/judge-rules.md`).
- A pattern rule: `metadata.why` in its rule file.
- Optionally, where the rule comes from: a `Source:` line in the Why section, or
  `metadata.source`. A link to public documentation, or the bug, PR comment or team
  decision behind it.

A gate is a judge rule's trigger, not a rule, and needs no why.

## Pattern rules

- Match the shape only where it breaks the convention, not everywhere it appears.
  `stopBy: end` on `has` or `inside` searches every descendant or ancestor; in a
  positive match, use it only when the shape breaks the convention in every position.
- Put the reason and the fix in the rule's `note`, not in comments in the rule's file.
  codeguard prints the note under the diagnostic, so it is what the blocked agent reads.
- Scope a rule with a binding, `bindings/<id>.yaml` with `rule`, `paths` and
  `exclude_paths`, never with ast-grep's `files` or `ignores`, so a project can change
  the scope. The exception is a rule whose convention is about which file code belongs
  in.
- When syntax decides only some shapes a violation takes, write a pattern rule for those
  shapes and a judge rule gated on every shape. No judge rule runs on a file with an
  `error` diagnostic, so the two report the same code only if the pattern rule is a
  `warning`.

## Cases

- Use made-up code and names, so a case shows the pattern rather than
  one class in the codebase. A public rule package never holds code copied from a
  private repository.
- Give idiomatic code a `valid` case beside the `invalid` one, so a rule that flags
  idiomatic code fails a case.
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
