# A judge rule's files

A judge rule is three files, all named by its id. In a project they sit under
`.codeguard/`; in a rule package, under the ruleset's directory.

## The skill: `skills/<id>/SKILL.md`

The convention the judge checks, written as `references/judge-rules.md` says. A rule in
several languages adds a supplement per language beside it, named after the language:
`python.md`, `typescript.md`, `ruby.md` or `javascript.md`.

## The binding: `bindings/<id>.yaml`

```yaml
skill: .codeguard/skills/<id>      # the skill's directory, from the repository root
paths: ["src/**/*.py"]             # the files the rule reviews
triggers: [return-yield, my-gate]  # the code a change must touch to be judged
```

- `exclude_paths` is optional: files to leave out of `paths`.
- Each trigger is a built-in change kind or the id of a gate, an ast-grep rule in
  `gates/<id>.yml`. The change kinds are `comment`, `docstring`, `import`,
  `function-signature`, `function-body`, `test-function`, `fixture`, `helper-function`,
  `class-header`, `class-attribute`, `module-statement`, `annotation`, `call`,
  `control-flow`, `return-yield`, `collection-literal`, `string-literal`,
  `number-literal`, `attribute-access`, `subscript`, `conditional-expression`,
  `membership-test`, `assert`, `raise`, `definition-added-or-removed`, `code` and `any`.
- Leave out `provider` and `model` unless the rule must be judged by another model.

## The rule eval: `rule-evals/<id>.yaml`

The file holds a `cases` list and nothing else. Each case is an edit and the outcome its
review should get:

```yaml
cases:
  - name: a getter that saves surprises a caller who only reads
    inputs:
      file: src/shop/orders.py
      before: |
        def get_order(number):
            return Order.objects.get(number=number)
      after: |
        def get_order(number):
            order = Order.objects.get(number=number)
            order.viewed_at = now()
            order.save()
            return order
    expected_output:
      outcome: invalid
```

- `name`: why the edit breaks or keeps the convention, unique in the file.
- `inputs.file`: the edited file's path from the repository root. It matches the
  binding's `paths`.
- `inputs.after`: the whole file after the edit. `inputs.before`: the whole file before
  it; leave it out for a new file.
- `inputs.unchanged`: optional, a map from the path of each other file the judge needs
  to read to its text.
- `expected_output.outcome`: `invalid` (the triggers fire and the judge reports a
  violation), `valid` (the triggers fire and the judge reports none) or `skipped` (the
  triggers don't fire).
