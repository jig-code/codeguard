# Writing a pattern rule

## Write its files

- The rule, `rules/pattern/<id>.yml`. A pattern rule matches one language.
- The binding, `bindings/<id>.yaml`. It sets `rule` (the rule's id), `paths` (globs of
  the files the rule reviews) and optionally `exclude_paths`.
- The tests, `rule-tests/<id>-test.yml`. Never put them under `rules/`: every YAML file
  there loads as a rule.

## Write the rule

- Match a shape only where it breaks the rule, not everywhere the shape appears.
  `stopBy: end` on `has` or `inside` searches every descendant or ancestor: in a positive
  match, use it only when the shape breaks the rule in every position.
- Put the rule's why in `metadata.why`, and where the rule comes from, if you give it, in
  `metadata.source`.
- Put the rule's why and the fix in its `note`, not in comments in the rule's file.
  codeguard prints the note under the diagnostic, so the note is what the blocked agent
  reads.
- Set `severity` in the rule file.
- Scope the rule with its binding's `paths` and `exclude_paths`, never with ast-grep's
  `files` or `ignores`, so that a project can change the scope. The exception is a rule
  whose convention is about which file code belongs in.

## Write its tests

- Give each branch of the rule one `valid` or `invalid` case, so that deleting a branch
  fails a case. Put a comment above each case naming its branch.
- Give each shape the rule matches that can keep the rule a `valid` case in which it
  keeps it, so that a rule that matches too widely fails a case.
- Leave the codebase clean for a new rule: fix each piece of code that breaks it, or put
  an `ast-grep-ignore: <id>` comment on the line above that code.
