# Writing a pattern rule

## Write the files

- The rule, `rules/pattern/<id>.yml`. A pattern rule matches one language.
- The binding, `bindings/<id>.yaml`. It sets `rule` (the rule's id), `paths` (globs of
  the files the rule reviews) and optionally `exclude_paths`.
- The tests, `rule-tests/<id>-test.yml`. Never put them under `rules/`: every YAML file
  there loads as a rule.

## Write the rule

- Match a shape only where it breaks the rule, not everywhere the shape appears.
  `stopBy: end` on `has` or `inside` searches every descendant or ancestor: outside a
  `not`, use it only when the shape breaks the rule in every position.
- Put the rule's why in `metadata.why`, and in its `note` with the fix. Put neither the
  why nor the fix in comments. codeguard prints the note under each report, so the note is
  what whoever fixes the code reads.
- Set `severity` in the rule file.
- Scope the rule with its binding's `paths` and `exclude_paths`, never with ast-grep's
  `files` or `ignores`, so that a project can change the scope. The exception is a rule
  whose convention is about which file code belongs in.

## Write its tests

- Give each branch of the rule, each sub-rule under `any`, `all` or `not`, one `valid`
  or `invalid` case, so that deleting a branch fails a case. Put a comment above each
  case that names its branch and the situation it tests.
- For each shape the rule matches, add a `valid` case in which that shape keeps the
  rule, so that a rule that matches too widely fails a case.
