# Writing a pattern rule

- Match a shape only where it breaks the rule, not everywhere it appears. `stopBy: end`
  on `has` or `inside` searches every descendant or ancestor; in a positive match, use it
  only when the shape breaks the rule in every position.
- Put the reason and the fix in the rule's `note`, not in comments in the rule's file. codeguard prints
  the note under the diagnostic, so it is what the blocked agent reads.
- Scope a rule with a binding, `bindings/<id>.yaml` with `rule`, `paths` and
  `exclude_paths`, never with ast-grep's `files` or `ignores`, so a project can change
  the scope. The exception is a rule whose convention is about which file code belongs
  in.
- When syntax decides only some of the shapes that would break the rule, the convention
  needs judgment: write a judge rule, not a pattern rule.
- Give each branch of the rule one `valid` or `invalid` case, so deleting a branch fails
  a case, with a comment above each case naming its branch. Give each matched shape a
  `valid` case where the convention allows it, if it has such a position, so a rule that
  matches too widely fails a case.
- Leave the codebase clean for a new rule: fix each piece of code that breaks it, or put
  an `ast-grep-ignore: <id>` comment on the line above it.
