---
name: writing-rules
description: Writes and changes codeguard rules, with their bindings, tests and evals: any file under .codeguard/ or in a codeguard rule package. Use whenever someone asks for a codeguard rule, asks to change one, or asks codeguard to check a convention, even if you already know ast-grep.
---

# Writing codeguard rules

A pattern rule is an ast-grep rule that matches code by its syntax. A judge rule states a
convention in prose, and a model judges each change against it.

Write every part of a rule in plain, clear words that a developer new to the project
understands on the first read.

## Workflow

1. Choose the tool, as Choosing a tool says.
2. For a judge rule, read `references/judge-rules.md`. For a pattern rule, read
   `references/pattern-rules.md`.
3. Write the rule and its other files as that reference says, and follow Every rule and
   Cases.

## Choosing a tool

An exact tool is any linter, type checker or similar tool for the project's language. It
gives the same answer on every run. Choose the tool by what decides whether code keeps or
breaks the rule, not by the words of the request.

- When an exact tool can check the convention, directly or through its configuration,
  write no rule, and say that the convention isn't codeguard's to check. This holds
  whether or not the project runs that tool or turns that check on. A way past the tool
  that the tool's configuration can forbid doesn't make the convention need judgment.
- Write a pattern rule for a code shape in one file that an exact tool could check only
  with a custom rule.
- Write a judge rule for a convention that needs judgment. Never write one for a
  convention that syntax or types decide. When syntax decides only some of the code that
  would break the rule, the convention needs judgment.

## Every rule

- Put a rule's files in the project's `.codeguard/` directory. In a rule package, a
  repository with `codeguard-package.yaml`, put them in the ruleset's directory instead.
  The references give each file's path inside that directory.
- Write one rule for each convention a request holds.
- Before writing a rule, read the project's own rules and the rulesets that
  `.codeguard/config.yaml` opts into.
- Code that another rule requires never breaks the new rule.
- Code that breaks another rule never breaks the new rule too. When code would break both
  rules, narrow one rule so that only the other covers that code, or merge the two rules.
- Idiomatic code, written the way the language and its libraries intend, keeps the rule.
  A shape isn't idiomatic in the project's own code just because a framework uses it.
- Name a specific class, function or file only when the convention is about that one.
  For a convention about many, describe what they share. Never name one of them to stand
  for the rest.
- Give every rule a why: the harm the rule prevents, in one or two sentences, so that
  whoever changes the code or the design around it can tell whether the rule still
  holds. You can also give where the rule comes from: a link to public documentation, or
  the bug, PR comment or team decision behind it.
- Set `severity: error` on a rule that must block. `warning` only reports.
- To change a rule from a ruleset for this project, override or exclude it in
  `.codeguard/config.yaml`. Never copy it into `.codeguard/`.
- When you think a diagnostic is wrong, fix the rule or its cases. Never change the
  reviewed code, or override or exclude the rule, to get past the diagnostic.

## Cases

A case is a pattern rule's test case or a judge rule's eval case.

- Use made-up code and names, so that a case shows the convention rather than one class
  in the codebase. A public rule package never holds code copied from a private
  repository.
- Give idiomatic code a `valid` case beside the `invalid` one.
- Give each case a name that says only the situation it tests, unique within its file.
  State the expected outcome once: in an eval case's `expected_output`, or by the `valid`
  or `invalid` list that a test case is in.
- Before writing a case, say in one sentence what its code does. If another case already
  has that sentence, don't write the case. Two cases whose code breaks or keeps the rule
  on the same ground are one case, however their syntax or names differ. Two `valid`
  cases differ only when their code keeps the rule in different situations.
- Make each case break the rule in one way at most: the way it tests. Read every other
  line of the case as a reviewer would, and rewrite any line that is wrong for another
  reason.
