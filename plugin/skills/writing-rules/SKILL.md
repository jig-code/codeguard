---
name: writing-rules
description: Writes and changes codeguard rules, with their tests and snapshots: any file under .codeguard/ or in a codeguard rule package. Use whenever someone asks for a codeguard rule or asks codeguard to check a convention, even if you already know ast-grep.
---

# Writing codeguard rules

A pattern rule is an ast-grep rule that matches code by its syntax. A judge rule states a
convention in prose, and a model judges each change against it.

Write every part of a rule in plain, clear words that a developer new to the project
understands on the first read.

## Workflow

1. **Pick the tool.** Read `references/choosing-a-tool.md` before writing any rule.
2. **State the convention and why it exists.** Follow The convention and Why it exists,
   below. Then check the statement against each bullet under The convention and these
   two checks. Rewrite the statement until it meets them all:
   - Never drop a relative pronoun that a phrase needs.
   - Wherever a pronoun could mean more than one noun, write the noun instead.
3. **Write the rule and its cases.** Before writing any rule file, read
   `references/layout.md`. For a pattern rule or a gate, read
   `references/pattern-rules.md`. For a judge rule, read `references/judge-rules.md`.
   Then follow Cases, below.

## The convention

A rule states one convention, in one declarative sentence, at the level of intent and in
words that don't depend on the language. Each piece of code keeps the rule or breaks it,
and the statement alone decides which.

- The statement says what code must never do.
- The statement says what it forbids only one time.
- The statement says nothing about how code avoids what it forbids.
- **No reason or consequence.** Every clause of the statement describes what the code it
  forbids does. Why the convention exists, and what follows once that code has run,
  belong in the rule's why.
- **Abstract.** The statement states an intent, never a list of code shapes, values or
  names, so it also decides code that no list would name.
- **One convention.** When a request holds more than one convention, write one rule for
  each. Code that the statement doesn't decide goes to a rule of its own or is dropped,
  never kept as an extra clause beside the statement.
- **Scoped to the change.** The statement is decided by the code a change adds or edits,
  the function, class and module around that code, and the definitions of the names
  that code uses. Only a convention about something unique or consistent across the
  repository is decided by code beyond the change and its surroundings.
- **Idiomatic code keeps it.** Code written the way the language and its libraries
  intend never breaks the rule. A shape a framework uses isn't idiomatic in the project's
  own code for that reason alone. A statement that idiomatic code breaks is restated,
  not given an exception.
- **Decided by its wording, never by examples.** A case that the statement decides
  wrongly, or on the wrong ground, shows the statement is unclear: reword the statement
  until it decides the case.
- **Never contradicts another rule.** Code that another rule requires never breaks a new
  rule. The other rules are the project's own and those in the rulesets it opts into in
  `.codeguard/config.yaml`.
- **Never overlaps another rule.** Code that breaks another rule never also breaks a new
  rule. When code breaks both, move that code's shape to one rule, or merge the two
  rules.
- **A rule names a specific class, function or file only when its convention is about
  that one.** A rule meant for many classes or functions describes what they share,
  never one of them standing in for the rest.

## Why it exists

Every rule has a why: the harm the rule prevents, in one or two sentences, so that
whoever changes the code or the design around it can tell whether the rule still holds.
A judge rule's why is its rule file's `## Why` section; a pattern rule's is
`metadata.why`, and its note repeats it. Optionally, give where the rule comes from: a
link to public documentation, or the bug, PR comment or team decision behind it. It goes
on a `Source:` line at the end of a judge rule's Why, or in a pattern rule's
`metadata.source`.

## Cases

- Use made-up code and names, so a case shows the convention rather than one class in
  the codebase. A public rule package never holds code copied from a private repository.
- Give idiomatic code a `valid` case beside the `invalid` one.
- A case's name gives only the situation it tests, unique per file. The expected outcome
  is stated once: in a rule eval case's `expected_output`, or by the `valid` or `invalid`
  list a test case sits in.
- Two cases that break or keep the rule on the same ground are one case, however their
  syntax or names differ: keep the clearer one. Two `valid` cases differ when their code
  keeps the rule in different situations, not merely by both not breaking it. Before
  writing a case, say in one sentence what its code does; if another case already has
  that sentence, don't write the case.
- A case breaks the rule in one way at most, the one it tests. Read every other line of
  it as a reviewer would, and rewrite any line that is wrong for another reason, so
  nothing else in the case can decide its outcome.

## Every rule

- Set `severity: error` on a rule that must block; `warning` only reports. A pattern
  rule's severity is in its rule file, a judge rule's in its binding.
- A diagnostic you think is wrong is fixed in the rule or its cases, never by changing
  the reviewed code to get past it.
