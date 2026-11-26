# Writing a judge rule

## Write all three files

A judge rule is one file, with a binding and a rule eval beside it. Write all three
files in the same pass.

- The rule file, `rules/judge/<id>.md`. The rule's id is the file's name without `.md`.
- The binding, `bindings/<id>.yaml`. It sets:
  - `rule`: the rule's id;
  - `paths`: globs of the files the rule reviews;
  - `triggers`: the change kinds or gates that call the judge;
  - optionally `exclude_paths`, and `severity`, which defaults to `error`.
- The rule eval, `rule-evals/<id>.yaml`. It holds `cases`, each with:
  - `name`;
  - `inputs`, which holds:
    - `file`: the changed file's path;
    - `before`: the file before the change, left out for a new file;
    - `after`: the file after the change;
    - optionally `unchanged`: a map from the path of each other file that the change
      needs to that file's text;
  - `expected_output`, which holds `outcome`: `invalid`, `valid` or `skipped`.

A convention that holds in several languages is one rule. Its binding's `paths` name
each language by file extension, and its rule eval has an `invalid` case in each
language.

## Write the rule file

The rule file is plain Markdown with no frontmatter. It holds only these, in this order:

1. A `#` title.
2. The statement, directly under the title, with no heading of its own.
3. `## Why`, which holds only the harm that the rule prevents.

## Write the statement

The statement is one declarative sentence. Code keeps the rule or breaks it, and the
statement alone decides which. Check the statement against each of these, and rewrite it
until it meets them all:

- The statement states one convention.
- The statement has no clause for code that the convention doesn't decide.
- The statement says what code must never do.
- The statement says what it forbids only once.
- A limit is a part of the statement that leaves some code out of what it forbids.
  Every limit in the statement leaves out only harmless code, by the harm that `## Why`
  names.
- The statement says nothing about how code avoids what it forbids.
- The statement says nothing about why the convention exists or what happens when code
  breaks the rule. Those go in `## Why`.
- The statement names what all the code that breaks the rule has in common, never
  particular things that code does or uses. A particular thing is something that only
  some of the code that breaks the rule does or uses. Naming one, even as an example,
  narrows the rule to what it names.
- The statement writes every relative pronoun that a phrase needs.
- Where a pronoun could mean more than one noun, the statement writes the noun.

When idiomatic code breaks the statement, or the statement decides a case wrongly or for
the wrong reason, reword what the statement says the code that breaks the rule has in
common until it decides that case rightly. Never add a clause that lets the case's code
keep the rule, or an example or the case's code to the rule file: either fits the rule
to that one case, and the rule still decides other code like it wrongly.

## Trigger on every shape of the code that breaks the rule

The judge sees a changed file only when a changed line falls inside a node that one of
the binding's `triggers` matches. Code that breaks the rule outside those nodes is never
reported.

- List the shapes that code breaking the rule takes, and make sure a trigger matches
  each one.
- Trigger on the code that breaks the rule, which can be in a different file from what
  the rule is about.
- Trigger on the narrowest node that holds the code that breaks the rule. A wider
  trigger costs judge calls. `any` calls the judge on every change, and `code`,
  `function-body` and `function-signature` on almost every change. `codeguard test` warns
  on all four.
- A trigger is a change kind or a gate. A change kind is a kind of code that codeguard
  finds in a changed file. The change kinds are `comment`, `docstring`, `import`,
  `function-signature`, `function-body`, `test-function`, `fixture`, `helper-function`,
  `class-header`, `class-attribute`, `module-statement`, `annotation`, `call`,
  `control-flow`, `return-yield`, `collection-literal`, `string-literal`,
  `number-literal`, `attribute-access`, `subscript`, `conditional-expression`,
  `membership-test`, `assert`, `raise`, `definition-added-or-removed`, `code` and `any`.
- When no change kind fits the node, write a gate with its own id, `<gate-id>`, and name
  that id in the binding's `triggers`.
- Write the gate in `gates/<gate-id>.yml` with only these keys:
  ```yaml
  id: <gate-id>
  language: python
  rule:
    <an ast-grep rule that matches the node>
  ```
- Write the gate's tests in `rule-tests/<gate-id>-test.yml`: a case for each branch, as
  `references/pattern-rules.md` says, and, for each shape the gate matches, an `invalid`
  case whose code the gate matches.
- Only Python has change kinds and gates. In a file in another language every trigger
  matches, so that language has no `skipped` case.

## Write a few clear eval cases

A rule eval has a few cases for each language:

- an `invalid` case for each different way that code breaks the rule;
- a `valid` case for each different situation in which code still clearly keeps the
  rule;
- a `skipped` case.

An `invalid` case breaks the rule beyond argument, and a `valid` case obviously keeps
it. A `skipped` case is a case whose change keeps the rule and matches no trigger. A
reader of the case alone sees why its code breaks or keeps the rule. Give each case only
the code that shows whether it breaks or keeps the rule.
