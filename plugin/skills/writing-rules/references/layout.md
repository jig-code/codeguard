# Where rule files go

- Pattern rule: `.codeguard/rules/pattern/<id>.yml`; its tests:
  `.codeguard/rule-tests/<id>-test.yml`, never under the rules directory (every YAML file
  there loads as a rule).
- Judge rule: the rule file `.codeguard/rules/judge/<id>.md`, the binding
  `.codeguard/bindings/<id>.yaml` and the rule eval `.codeguard/rule-evals/<id>.yaml`.
  Write all three in the same pass; a judge rule without its binding and rule eval is
  unfinished.
  - The rule file is plain Markdown, with no frontmatter; `references/judge-rules.md`
    says what it holds. The rule's id is the file's name without `.md`.
  - The binding sets `rule` (the rule's id), `paths` (globs of the files the rule
    reviews) and `triggers` (the change kinds or gates that run the rule; never `any`,
    `code`, `function-body` or `function-signature`, which match almost every change).
  - The rule eval holds `cases`, each with a `name`, `inputs` (`file`, the edited file's
    path; `before`, the file before the edit, left out for a new file; `after`, the
    file after it) and `expected_output` (`outcome`: `invalid`, `valid` or `skipped`).
- Gate: `.codeguard/gates/<id>.yml`, an ast-grep rule tested by
  `.codeguard/rule-tests/<id>-test.yml`.
- In a rule package (a repo with `codeguard-package.yaml`), the same layout sits under
  each ruleset's directory instead of `.codeguard/`.
- A convention that holds in several languages is one judge rule: its binding's paths
  name each language, and its eval has cases in each (codeguard's `docs/rule-formats.md`,
  A rule in several languages). Its rule file uses no language's names, syntax or
  libraries. A pattern rule matches one language.
- Before writing a rule, check the rulesets the project opts into in
  `.codeguard/config.yaml`. To change a packaged rule for this project, override or
  exclude it there; don't copy it into `.codeguard/`.

codeguard's `docs/rule-formats.md` has the binding and rule eval formats.
