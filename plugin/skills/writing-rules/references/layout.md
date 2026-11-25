# Where rule files go

- Pattern rule: `.codeguard/rules/pattern/<id>.yml`; its tests:
  `.codeguard/rule-tests/<id>-test.yml`, never under the rules directory (every YAML file
  there loads as a rule).
- Judge rule: the rule file `.codeguard/rules/judge/<id>.md`, the binding
  `.codeguard/bindings/<id>.yaml` and the rule eval `.codeguard/rule-evals/<id>.yaml`.
  A judge rule isn't written until all three exist; write the binding and the rule eval
  in the same pass as the rule file, never leave them for later.
  - The rule's id is the rule file's name without `.md`.
  - The binding sets `rule` (the rule's id), `paths` (globs of the files the rule
    reviews) and `triggers` (the change kinds or gates that call the judge, never `any`,
    `code`, `function-body` or `function-signature`).
  - The rule eval holds `cases`, each with a `name`, `inputs` and `expected_output`.
    `inputs` holds `file`, the edited file's path; `before`, the file before the edit,
    left out for a new file; `after`, the file after it; and optionally `unchanged`, a
    map from the path of each other file the edit needs to its text. `expected_output`
    holds `outcome`: `invalid`, `valid` or `skipped`.
- Gate: `.codeguard/gates/<id>.yml`, an ast-grep rule tested by
  `.codeguard/rule-tests/<id>-test.yml`.
- In a rule package (a repo with `codeguard-package.yaml`), the same layout sits under
  each ruleset's directory instead of `.codeguard/`.
- A judge rule whose convention holds in several languages is one rule: its binding's
  paths name each language by file extension, and its rule eval has an `invalid` case in
  each. Never copy a convention into a rule per language. A pattern rule matches one
  language.
- Before writing a rule, check the rulesets the project opts into in
  `.codeguard/config.yaml`. To change a packaged rule for this project, override or
  exclude it there; don't copy it into `.codeguard/`.
