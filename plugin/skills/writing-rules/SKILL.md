---
name: writing-rules
description: Writes and changes codeguard rules, with their bindings, tests and evals, or says when a convention isn't codeguard's to check. Use whenever someone asks for a codeguard rule, asks to change one, or asks codeguard to check a convention, even if you already know ast-grep.
---

# Writing codeguard rules

A pattern rule is an ast-grep rule that matches code by its syntax. A judge rule states a
convention in prose, and a model, the judge, decides whether each change keeps it.

## Workflow

1. For a new rule, or a change to what an existing rule's convention is, choose the tool
   as `references/choosing-a-tool.md` says.
2. When the choice is a static analysis tool other than codeguard, the convention isn't
   codeguard's to check. Tell the user that. Write no rule, and don't offer to write one or
   ask whether to.
3. For a judge rule, read `references/every-rule.md` and `references/judge-rules.md`. For
   a pattern rule, read `references/every-rule.md` and `references/pattern-rules.md`.
