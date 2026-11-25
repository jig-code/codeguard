# Writing a judge rule

## Write the rule file

The rule file, `rules/judge/<id>.md`, is plain Markdown with no frontmatter, and
codeguard's judge gets its text unparsed. It holds, in this order, and nothing else:

1. A `#` title.
2. The convention: one declarative sentence, stated as the writing-rules skill's The
   convention section says. It goes directly under the title, with no heading of its own.
3. `## Why`: the harm the rule prevents, in a sentence or two. The why never names code
   the statement doesn't decide.

Nothing else goes in the rule file, in any section or for any language: no fix, no
example, no exception for a case, and nothing about how to answer. A rule in several
languages is one rule file, in no language's names, syntax or libraries.

## Gate every form of the code that breaks the rule

The judge sees a changed file only when a changed line falls inside a node that one of
the binding's `triggers` matches, so code that breaks the rule outside them is never
reported.

- List the syntactic forms that code breaking the rule takes, and give each one an
  `invalid` gate test, so a gate that stops matching a form fails `codeguard test`.
- Gate on where code that breaks the rule appears, not on the rule's topic, which may be
  defined in another file.
- Gate on the narrowest node that holds the code that breaks the rule. A wider gate costs
  judge calls and tokens; `codeguard review --dry-run` counts the calls.
- A trigger is a built-in change kind or a gate. The built-in kinds are `comment`,
  `docstring`, `import`, `function-signature`, `function-body`, `test-function`,
  `fixture`, `helper-function`, `class-header`, `class-attribute`, `module-statement`,
  `annotation`, `call`, `control-flow`, `return-yield`, `collection-literal`,
  `string-literal`, `number-literal`, `attribute-access`, `subscript`,
  `conditional-expression`, `membership-test`, `assert`, `raise`,
  `definition-added-or-removed`, `code` and `any`. When no kind fits the node, write a
  gate: an ast-grep rule in `gates/<id>.yml` that matches the node, named in `triggers`
  and tested like a pattern rule.

## Write a few clear eval cases

A rule eval has a few cases per rule and language: one `invalid` case for each distinct
ground on which code breaks the convention, one `valid` case for each distinct situation
near the boundary in which code keeps it, and a `skipped` case outside the gate. Each
case tests one thing that none of the others does: a different thing the code does, not
another syntax for the same thing. No edge cases: a case that a reasonable reviewer could
argue either way proves nothing about the rule.

- An `invalid` case breaks the convention beyond argument, and a `valid` case obviously
  keeps it. A reader of the case alone sees why the code breaks or keeps it.
- A rule in several languages has cases in each, each case's `file` in its language.

A case is kept only while it is clear, tests something no other case does, and comes
from the statement or from a real miss. A new case comes only from a real miss: a review
that wrongly blocked code or wrongly let it through. Write it as the smallest clear case
of that miss, and never add its code to the rule file.
