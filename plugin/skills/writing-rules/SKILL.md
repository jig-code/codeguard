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
- **Code that uses the language and its libraries as their documentation shows never
  breaks the rule.** If such code breaks it, reword the statement rather than adding an
  exception.
- **Fix a wrong verdict by rewording.** An example or an exception fixes only that one
  case.
- **Don't contradict or repeat a configured rule.** Keeping the new rule must never force
  code to break a configured one. If both forbid the same code, keep it in one rule or
  merge the two.
- **Name a specific class, function or file only when the rule is about that one.**
  Otherwise, describe what the group has in common.

## Why it exists

Every rule says what harm it prevents, in one or two sentences, so anyone can tell
whether it still matters when the code around it changes. A rule with no reason can only
be kept or dropped blind.

- A judge rule: a `## Why` section in its rule file (`references/judge-rules.md`).
- A pattern rule: `metadata.why` in its rule file.
- Optionally, say where the rule comes from: a `Source:` line in the Why section, or
  `metadata.source`.

A gate is a judge rule's trigger, not a rule, and needs no why.

## Pattern rules

- Match the shape only where it breaks the rule. `stopBy: end` on `has` or `inside`
  searches every descendant or ancestor, so in a positive match, use it only when the
  shape breaks the rule wherever it sits.
- Put the reason and the fix in the rule's `note`, not in comments: codeguard prints the
  note under each finding, so it's what the blocked agent reads.
- Set a rule's scope with a binding (`bindings/<id>.yaml` with `rule`, `paths` and
  `exclude_paths`), never with ast-grep's `files` or `ignores`, so a project can change
  it. The exception is a rule about which file code belongs in.
- When syntax decides only some forms of a violation, write a pattern rule for those and
  a judge rule for all of them. No judge rule runs on a file with an `error` finding, so
  make the pattern rule a `warning` if both should report the same code.

## Cases

- Use made-up code and names, so a case shows the rule rather than one class in the
  codebase. A public rule package never holds code copied from a private repository.
- Add a `valid` case of code that uses the language and its libraries as their
  documentation shows, so a rule that this code breaks fails a case.
- A pattern rule: one case per branch, with a comment above it naming the branch, so
  deleting a branch fails a case. Where a matched shape is allowed in some position,
  give that position a `valid` case, so a rule that matches too widely fails a case.
- A judge rule: a few clear `invalid` and `valid` cases, and a `skipped` case outside
  the gate (`references/judge-rules.md`).
- Name a case by the situation it tests, unique in its file. State its verdict once: in
  a rule eval case's expected outcome, or by the `valid` or `invalid` list a test case
  sits in.
- Give each case a situation no other case tests. Cases whose code differs only in names
  or syntax test the same situation. A `valid` case's situation is how its code keeps
  the rule, not just that the violation is missing.
- Give a case one defect at most, the one it tests. Fix any other line a reviewer would
  object to, so nothing else decides the verdict.

## Every rule

- Set `severity: error` on a rule that must block; `warning` only reports.
- Fix a finding you think is wrong in the rule or its cases, never by changing the
  reviewed code to get past it.
- Leave the codebase clean for a new rule: fix each existing violation, or put an
  `ast-grep-ignore: <id>` comment on the line above it.
