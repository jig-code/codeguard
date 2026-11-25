---
name: writing-rules
description: Writes and changes codeguard rules, with their bindings, tests and evals, or says when a convention isn't codeguard's to check. Use whenever someone asks for a codeguard rule, asks to change one, or asks codeguard to check a convention, even if you already know ast-grep.
---

# Writing codeguard rules

A pattern rule is an ast-grep rule that matches code by its syntax. A judge rule states a
convention in prose, and a model, the judge, decides whether each change keeps it.

## Workflow

1. Choose the tool, as Choosing a tool says. When the convention isn't codeguard's to
   check, write no rule, say so, and stop.
2. Read `references/every-rule.md`. Then, for a judge rule, read
   `references/judge-rules.md`; for a pattern rule, read `references/pattern-rules.md`.

## Choosing a tool

Three tools can check a convention: an exact tool, a pattern rule and a judge rule. An
exact tool is any linter, type checker or similar tool for the project's language, and
gives the same answer on every run. Choose the tool by what decides whether code keeps or
breaks the rule, not by the words of the request.

- When an exact tool can check the convention, directly or by turning on a check that
  the exact tool ships with, the convention isn't codeguard's to check. This holds
  whether or not the project runs that exact tool or turns that check on. It also holds
  when code can turn the check off, as long as the exact tool's configuration can forbid
  turning it off.
- Write a pattern rule when the convention is about a code shape within one file, and an
  exact tool could check that shape only through a custom rule. A rule that you would
  write yourself in the exact tool's configuration counts as a custom rule.
- Write a judge rule for a convention that needs judgment. Never write one for a
  convention that syntax or types decide. When syntax decides only some of the code that
  would break the rule, the convention needs judgment.
