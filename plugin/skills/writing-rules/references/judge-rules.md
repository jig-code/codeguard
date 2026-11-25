# Writing a judge rule

## Write the rule file

The rule file, `rules/judge/<id>.md`, is plain Markdown with no frontmatter, and
codeguard's judge gets its text unparsed. It holds, in this order, and nothing else:

1. A `#` title.
2. The statement: one declarative sentence, written as The convention section of
   `SKILL.md` says. It goes directly under the title, with no heading of its own.
3. `## Why`: the harm the rule prevents, in a sentence or two. The why never names code
   the statement doesn't decide.

Nothing else goes in the rule file, in any section or for any language: no fix, no
example, no exception for a case, and nothing about how to answer. The rule file uses no
language's names, syntax or libraries.

## Trigger on every shape of the code that breaks the rule

The judge sees a changed file only when a changed line falls inside a node that one of
the binding's `triggers` matches, so code that breaks the rule outside them is never
reported.

- List the shapes that code breaking the rule takes, and make sure a trigger matches
  each one. Give a gate an `invalid` test case for each shape it matches, so a gate that
  stops matching a shape fails `codeguard test`.
- Trigger on the code that breaks the rule, which can be in a different file from what
  the rule is about.
- Trigger on the narrowest node that holds the code that breaks the rule. A wider trigger
  costs judge calls and tokens; `codeguard review --dry-run` counts the calls.
- A trigger is a built-in change kind or a gate. The built-in kinds are `comment`,
  `docstring`, `import`, `function-signature`, `function-body`, `test-function`,
  `fixture`, `helper-function`, `class-header`, `class-attribute`, `module-statement`,
  `annotation`, `call`, `control-flow`, `return-yield`, `collection-literal`,
  `string-literal`, `number-literal`, `attribute-access`, `subscript`,
  `conditional-expression`, `membership-test`, `assert`, `raise`,
  `definition-added-or-removed`, `code` and `any`. When no kind fits the node, write a
  gate, which is an ast-grep rule that matches the node, and name it in `triggers`.
- Only Python has change kinds and gates. In a file in another language every trigger
  fires, so that language has no `skipped` case.

## Write a few clear eval cases

A rule eval has a few cases per rule and language: one `invalid` case for each distinct
ground on which code breaks the rule, one `valid` case for each distinct situation close
to code that breaks the rule in which code still clearly keeps it, and a `skipped` case
that no trigger matches. No edge cases: a case that a reasonable reviewer could argue
either way proves nothing about the rule.

- An `invalid` case breaks the rule beyond argument, and a `valid` case obviously
  keeps it. A reader of the case alone sees why the code breaks or keeps it.

A case is kept only while it is clear, tests something no other case does, and comes
from the statement or from a real miss. Once the rule has its first cases, a new case
comes only from a real miss: a review that wrongly blocked code or wrongly let it
through. Write it as the smallest clear case of that miss, and never add its code to the
rule file.
