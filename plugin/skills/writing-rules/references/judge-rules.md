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
  - `inputs`, which holds `file`, the changed file's path; `before`, the file before the
    change, left out for a new file; `after`, the file after the change; and optionally
    `unchanged`, a map from the path of each other file the change needs to that file's
    text;
  - `expected_output`, which holds `outcome`: `invalid`, `valid` or `skipped`.

A convention that holds in several languages is one rule. Its binding's `paths` name
each language by file extension, and its rule eval has an `invalid` case in each
language.

## Write the rule file

The rule file is plain Markdown with no frontmatter. It holds these, in this order:

1. A `#` title.
2. The statement, directly under the title, with no heading of its own.
3. `## Why`: the rule's why. The why mentions only code that the statement decides. To
   give where the rule comes from, end the section with a `Source:` line.

The rule file holds nothing else: no fix, no example, no exception for particular code,
and no instructions for the judge. The rule file uses no programming language's syntax,
and names a language, library or API only when the convention is about that one.

## Write the statement

The statement is one declarative sentence. Code keeps the rule or breaks it, and the
statement alone decides which. Check the statement against each of these, and rewrite it
until it meets them all:

- The statement states one convention, and has no clause for code that the convention
  doesn't decide. Give that code a rule of its own, or leave it out.
- The statement says what code must never do.
- The statement says what it forbids only once.
- The statement says nothing about how code avoids what it forbids.
- The statement says nothing about why the convention exists or what happens when code
  breaks the rule. Those go in `## Why`.
- The statement names what the forbidden code has in common, never a list of code
  shapes, values or names. A list
  decides only what it names.
- The statement can be decided from the code a change adds or edits, read with the
  function, class and module around that code and the definitions of the names that
  code uses. Only a convention that something stays unique or consistent across the
  repository needs code beyond that.
- The statement writes every relative pronoun that a phrase needs.
- Where a pronoun could mean more than one noun, the statement writes the noun.

When idiomatic code breaks the statement, or the statement decides a case wrongly or for
the wrong reason, reword the statement. Never add an exception, an example or the case's
code to the rule file.

## Trigger on every shape of the code that breaks the rule

The judge sees a changed file only when a changed line falls inside a node that one of
the binding's `triggers` matches. Code that breaks the rule outside those nodes is never
reported.

- List the shapes that code breaking the rule takes, and make sure a trigger matches
  each one.
- Trigger on the code that breaks the rule, which can be in a different file from what
  the rule is about.
- Trigger on the narrowest node that holds the code that breaks the rule. A wider
  trigger costs judge calls. `any`, `code`, `function-body` and `function-signature` call
  the judge on almost every change, and `codeguard test` warns on them.
- A trigger is a change kind or a gate. The change kinds are `comment`,
  `docstring`, `import`, `function-signature`, `function-body`, `test-function`,
  `fixture`, `helper-function`, `class-header`, `class-attribute`, `module-statement`,
  `annotation`, `call`, `control-flow`, `return-yield`, `collection-literal`,
  `string-literal`, `number-literal`, `attribute-access`, `subscript`,
  `conditional-expression`, `membership-test`, `assert`, `raise`,
  `definition-added-or-removed`, `code` and `any`.
- When no change kind fits the node, write a gate: an ast-grep rule in `gates/<id>.yml`
  that matches the node. Name the gate in `triggers`. Write the gate, and its tests in
  `rule-tests/<id>-test.yml`, as `references/pattern-rules.md` says for a pattern rule.
  A gate's `invalid` cases are code the gate matches: give it one for each shape it
  matches, so that a gate that stops matching a shape fails `codeguard test`.
- Only Python has change kinds and gates. In a file in another language every trigger
  matches, so that language has no `skipped` case.

## Write a few clear eval cases

A rule eval has a few cases for each language:

- an `invalid` case for each different way that code breaks the rule;
- a `valid` case for each different situation, close to code that breaks the rule, in
  which code still clearly keeps it;
- in Python, a `skipped` case whose change no trigger matches.

An `invalid` case breaks the rule beyond argument, and a `valid` case obviously keeps
it. A reader of the case alone sees why its code breaks or keeps the rule. Write no case
that a reasonable reviewer could argue either way: it shows nothing about the rule.

Write the first cases from the statement. Keep a case only while it is clear. Once the
rule has its first cases, add a case only for a real miss: a review that wrongly blocked
code or wrongly let it through. Write the smallest clear case of that miss.
